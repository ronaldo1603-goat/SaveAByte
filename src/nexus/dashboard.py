# src/dashboard.py
import numpy as np
import pandas as pd
import streamlit as st

from src.nexus import style
from src.nexus.db import fetch_logs, fetch_taps, latest_calibration, signed_url

NGUONG_GIAM = 0.30
NGUONG_TANG = 0.15
TAP_CAO = 0.15 


def tinh_khuyen_nghi(waste: float, tap_rate: float) -> tuple[str, str]:
    if waste >= NGUONG_GIAM and tap_rate >= TAP_CAO:
        return "Cần xem xét", "Vừa bỏ nhiều vừa xin thêm nhiều — khẩu vị chia rẽ, không phải vấn đề định lượng"
    if waste >= NGUONG_GIAM:
        return f"Giảm ~{int(waste * 100 * 0.5)}%", "Tỉ lệ thừa cao, ít người xin thêm"
    if waste < NGUONG_TANG and tap_rate >= TAP_CAO:
        return "Tăng định lượng", "Ăn gần hết và nhiều người xin thêm — suất đang thiếu"
    return "Giữ nguyên", "Trong ngưỡng hợp lý"


def build_dashboard(start_date: str, end_date: str) -> None:
    logs = fetch_logs(start_date, end_date)
    taps = fetch_taps(start_date, end_date)

    if "phase" in logs.columns:
        logs = logs[logs["phase"] == "after"].copy()

    if logs.empty:
        st.warning("Chưa có dữ liệu quét khay trong khoảng thời gian này.")
        return

    logs["dish_name"] = logs["dish_name"].str.strip().str.lower()
    if not taps.empty:
        taps["dish_name"] = taps["dish_name"].str.strip().str.lower()

    if "inedible_ratio" not in logs.columns:
        logs["inedible_ratio"] = 0.0
    logs["edible_waste"] = logs["fill_fraction"] * (1 - logs["inedible_ratio"].fillna(0))

    so_khay = logs["scan_id"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Số khay đã quét", so_khay)
    c2.metric("Tỉ lệ thừa trung bình", f"{logs['edible_waste'].mean():.0%}")
    c3.metric("Lượt xin thêm", len(taps))

    st.divider()

    per_dish = (
        logs.groupby("dish_name")
        .agg(thua_tb=("edible_waste", "mean"), so_lan=("edible_waste", "size"))
        .reset_index()
    )

    if taps.empty:
        per_dish["xin_them"] = 0
    else:
        tap_count = taps.groupby("dish_name").size().rename("xin_them")
        per_dish = per_dish.merge(tap_count, on="dish_name", how="left")
        per_dish["xin_them"] = per_dish["xin_them"].fillna(0).astype(int)

    per_dish["tap_rate"] = per_dish["xin_them"] / so_khay

    ket_qua = per_dish.apply(
        lambda r: tinh_khuyen_nghi(r["thua_tb"], r["tap_rate"]), axis=1
    )
    per_dish["khuyen_nghi"] = [k for k, _ in ket_qua]
    per_dish["ly_do"] = [l for _, l in ket_qua]

    per_dish = per_dish.sort_values("thua_tb", ascending=False)
    per_dish["thua_pct"] = per_dish["thua_tb"] * 100

    st.subheader("Khuyến nghị điều chỉnh định lượng")
    st.dataframe(
        per_dish[["dish_name", "thua_pct", "xin_them", "khuyen_nghi", "ly_do"]],
        column_config={
            "dish_name": "Món",
            "thua_pct": st.column_config.ProgressColumn(
                "Tỉ lệ thừa", min_value=0.0, max_value=100.0, format="%.0f%%"
            ),
            "xin_them": "Lượt xin thêm",
            "khuyen_nghi": "Khuyến nghị",
            "ly_do": "Căn cứ",
        },
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        f"Dựa trên {so_khay} khay. Ngưỡng phân loại hiện là tạm thời, "
        "cần hiệu chỉnh bằng đối chiếu với khay cân thực tế."
    )

def prepare(logs: pd.DataFrame) -> pd.DataFrame:
    df = logs.copy()
    if df.empty:
        return df

    df["dish_name"] = df["dish_name"].str.strip().str.lower()

    if "inedible_ratio" not in df.columns:
        df["inedible_ratio"] = 0.0
    if "phase" not in df.columns:
        df["phase"] = "after"

    df["inedible_ratio"] = df["inedible_ratio"].fillna(0.0)
    df["edible_waste"] = df["fill_fraction"] * (1 - df["inedible_ratio"])
    return df


def daily_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not (df["phase"] == "after").any():
        return pd.DataFrame()

    g = (df.groupby(["meal_date", "dish_name", "phase"])["edible_waste"]
           .agg(mean="mean", std="std", n="count")
           .reset_index())

    before = (g[g["phase"] == "before"]
              .rename(columns={"mean": "mean_before",
                               "std": "std_before",
                               "n": "n_before"})
              .drop(columns="phase"))

    after = (g[g["phase"] == "after"]
             .rename(columns={"mean": "mean_after",
                              "std": "std_after",
                              "n": "n_after"})
             .drop(columns="phase"))

    wide = after.merge(before, on=["meal_date", "dish_name"], how="left")

    measured = wide["mean_before"].notna()
    fallback = wide.groupby("dish_name")["mean_before"].transform("mean")
    wide["mean_before"] = wide["mean_before"].fillna(fallback)
    wide["before_source"] = np.select(
        [measured, wide["mean_before"].notna()],
        ["measured", "imputed"],
        default="missing",        
    )

    valid = wide["mean_before"] > 0

    wide["waste_ratio"] = np.where(
        valid, wide["mean_after"] / wide["mean_before"], np.nan
    )
    wide["portion_cv"] = np.where(
        valid, wide["std_before"] / wide["mean_before"], np.nan
    )

    wide["flag"] = np.where(wide["waste_ratio"] > 1, "check", "")

    return wide.sort_values(["meal_date", "dish_name"]).reset_index(drop=True)


def _wmean(values: pd.Series, weights: pd.Series) -> float:
    m = values.notna() & weights.notna()
    if not m.any() or weights[m].sum() == 0:
        return float("nan")
    return float((values[m] * weights[m]).sum() / weights[m].sum())


def weekly_table(wide: pd.DataFrame) -> pd.DataFrame:
    if wide.empty:
        return pd.DataFrame()

    out = []
    for dish, g in wide.groupby("dish_name"):
        out.append({
            "dish_name":    dish,
            "waste_ratio":  _wmean(g["waste_ratio"], g["n_after"]),
            "portion_cv":   g["portion_cv"].mean(),
            "n_days":       int(g["waste_ratio"].notna().sum()),
            "n_trays":      int(g["n_after"].sum()),
            "imputed_days": int((g["before_source"] == "imputed").sum()),
        })

    return (pd.DataFrame(out)
            .sort_values("waste_ratio", ascending=False)
            .reset_index(drop=True))


def apply_calibration(ratio: pd.Series, cal: dict | None) -> pd.Series:
    if not cal:
        return ratio
    return (cal["slope"] * ratio + cal["intercept"]).clip(0, 1)

def build_weekly(start_date: str, end_date: str) -> None:
    df = prepare(fetch_logs(start_date, end_date))
    daily = daily_table(df)
    week = weekly_table(daily)

    st.subheader("Tỉ lệ bỏ lại so với lượng phát ra")

    if week.empty or week["waste_ratio"].isna().all():
        style.empty("Chưa đủ dữ liệu để tính",
                    "Cần cả ảnh khay trước bữa (chế độ “Trước bữa”) và khay sau bữa trong khoảng này.")
        return

    cal = latest_calibration()
    mae = cal.get("mae") if cal else None

    show = week.copy()
    show["shown"] = apply_calibration(show["waste_ratio"], cal)

    def fmt(v):
        if pd.isna(v):
            return "—"
        return f"{v:.0%} ± {mae:.0%}" if mae is not None else f"{v:.0%}"

    show["Tỉ lệ bỏ lại"] = show["shown"].map(fmt)
    show["Độ đều khẩu phần"] = show["portion_cv"].map(
        lambda v: "—" if pd.isna(v) else ("đều" if v < 0.10 else "chênh lệch")
    )

    st.dataframe(
        show[["dish_name", "Tỉ lệ bỏ lại", "Độ đều khẩu phần", "n_days", "n_trays"]],
        column_config={"dish_name": "Món", "n_days": "Số ngày", "n_trays": "Số khay"},
        hide_index=True,
        use_container_width=True,
    )

    if mae is not None:
        st.caption(
            f"Đã hiệu chỉnh theo {cal['n']} khay cân thực tế (fit ngày {cal['fit_date']}). "
            f"±{mae:.0%} là sai số trung bình trên từng khay (MAE). "
            "Đã trừ phần không ăn được (xương, cọng, vỏ)."
        )
    else:
        st.warning("Chưa hiệu chỉnh với khay cân thực tế — con số chưa có biên sai số.")

    st.caption(
        "Số ngày = số ngày món có đủ ảnh trước và sau bữa. "
        "Món chỉ có 1 ngày chỉ nên tham khảo, chưa đủ để kết luận."
    )
    if (week["imputed_days"] > 0).any():
        st.caption("Ngày thiếu ảnh trước bữa được thay bằng trung bình các ngày khác của cùng món.")

    st.subheader("Diễn biến theo ngày")
    trend = daily.assign(shown=apply_calibration(daily["waste_ratio"], cal))
    st.line_chart(trend.pivot(index="meal_date", columns="dish_name", values="shown"))

    _audit_trail(df)

def _audit_trail(df: pd.DataFrame) -> None:
    after = df[df["phase"] == "after"]
    if after.empty:
        return
    with st.expander("Xem ảnh khay gốc (kiểm chứng AI)"):
        dish = st.selectbox("Món", sorted(after["dish_name"].unique()))
        sub = (after[(after["dish_name"] == dish) & after["image_url"].notna()]
               .sort_values("edible_waste", ascending=False)
               .drop_duplicates("scan_id")        # 1 khay chỉ hiện 1 lần
               .head(6))
        cols = st.columns(3)
        for i, (_, r) in enumerate(sub.iterrows()):
            try:
                cols[i % 3].image(signed_url(r["image_url"]),
                                  caption=f"còn {r['edible_waste']:.0%} ngăn")
            except Exception:
                cols[i % 3].caption("không tải được ảnh")

def slot_table(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["phase"] == "after"].copy()
    if d.empty:
        return pd.DataFrame()

    t = pd.to_datetime(d["created_at"], utc=True, format="ISO8601")
    t = t.dt.tz_convert("Asia/Ho_Chi_Minh")
    d["minute"] = t.dt.hour * 60 + t.dt.minute

    out = []
    for _, g in d.groupby("meal_date"):
        trays = g.drop_duplicates("scan_id")[["scan_id", "minute"]].copy()
        if len(trays) < 3:
            continue
        # rank(method="first") -> giá trị duy nhất -> qcut không vỡ khi nhiều khay trùng phút
        trays["slot"] = pd.qcut(trays["minute"].rank(method="first"), 3,
                                labels=["đầu", "giữa", "cuối"])
        out.append(g.merge(trays[["scan_id", "slot"]], on="scan_id"))

    if not out:
        return pd.DataFrame()

    allg = pd.concat(out)
    return (allg.groupby("slot", observed=True)
                .agg(mean=("edible_waste", "mean"), n_khay=("scan_id", "nunique"))
                .reset_index())