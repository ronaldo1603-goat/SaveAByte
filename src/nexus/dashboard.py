import numpy as np
import pandas as pd
import streamlit as st

from src.nexus import style
from src.nexus.db import (fetch_logs, fetch_menus, fetch_scans, fetch_servings,
                          fetch_taps, latest_calibration, signed_url)
from src.nexus.menu import normalize_dish

# Ngưỡng tạm thời, áp lên tỉ lệ bỏ lại so với suất phát ra. Cần hiệu chỉnh lại khi có dữ liệu thật.
NGUONG_GIAM = 0.30
NGUONG_TANG = 0.15
TAP_CAO = 0.15
NGUONG_CHE_BIEN = 0.50   # tạm thời, chưa hiệu chỉnh


def tinh_khuyen_nghi(waste: float, tap_rate: float) -> tuple[str, str]:
    if waste >= NGUONG_GIAM and tap_rate >= TAP_CAO:
        return "Xem lại cách chế biến", "Vừa bỏ nhiều vừa xin thêm nhiều — khẩu vị chia rẽ, không phải vấn đề định lượng"
    if waste >= NGUONG_CHE_BIEN:
        return "Thử đổi cách chế biến", "Bỏ lại hơn nửa, ít người xin thêm — giảm định lượng không đủ giải quyết"
    if waste >= NGUONG_GIAM:
        return f"Giảm ~{int(waste * 100 * 0.5)}%", "Tỉ lệ thừa cao, ít người xin thêm"
    if waste < NGUONG_TANG and tap_rate >= TAP_CAO:
        return "Tăng định lượng", "Ăn gần hết và nhiều người xin thêm — suất đang thiếu"
    return "Giữ nguyên", "Trong ngưỡng hợp lý"

def prepare(logs: pd.DataFrame) -> pd.DataFrame:
    df = logs.copy()
    if df.empty:
        return pd.DataFrame(columns=["scan_id", "image_url", "dish_name", "fill_fraction",
                                     "inedible_ratio", "meal_date", "phase", "edible_waste"])

    df["dish_name"] = df["dish_name"].map(normalize_dish)

    if "inedible_ratio" not in df.columns:
        df["inedible_ratio"] = 0.0
    if "phase" not in df.columns:
        df["phase"] = "after"

    df["inedible_ratio"] = df["inedible_ratio"].fillna(0.0)
    df["edible_waste"] = df["fill_fraction"] * (1 - df["inedible_ratio"])
    return df


def _served(df: pd.DataFrame, menus: pd.DataFrame) -> pd.DataFrame:
    inferred = df[["meal_date", "dish_name"]].drop_duplicates()
    if menus.empty:
        return inferred
    m = menus[["meal_date", "dish_name"]].drop_duplicates()
    legacy = inferred[~inferred["meal_date"].isin(m["meal_date"])]
    return pd.concat([m, legacy], ignore_index=True)


def per_day_dish(df: pd.DataFrame, scans: pd.DataFrame, menus: pd.DataFrame) -> pd.DataFrame:
    if scans.empty:
        return pd.DataFrame(columns=["meal_date", "dish_name", "waste_sum", "n_trays", "mean_after"])
    n_trays = (scans[scans["phase"] == "after"]
               .groupby("meal_date")["scan_id"].nunique()
               .rename("n_trays").reset_index())
    served = _served(df, menus)
    sums = (df[df["phase"] == "after"]
            .groupby(["meal_date", "dish_name"])["edible_waste"].sum()
            .rename("waste_sum").reset_index())
    out = (served.merge(sums, on=["meal_date", "dish_name"], how="left")
                 .merge(n_trays, on="meal_date", how="inner"))
    out["waste_sum"] = out["waste_sum"].fillna(0.0).astype(float)   # ngày ăn sạch hết: cột rỗng kiểu object
    out["mean_after"] = out["waste_sum"] / out["n_trays"]
    return out


def daily_table(df: pd.DataFrame, scans: pd.DataFrame, menus: pd.DataFrame) -> pd.DataFrame:
    after = per_day_dish(df, scans, menus).rename(columns={"n_trays": "n_after"})
    if after.empty:
        return pd.DataFrame()

    before = (df[df["phase"] == "before"]
              .groupby(["meal_date", "dish_name"])["edible_waste"]
              .agg(mean_before="mean", std_before="std", n_before="count")
              .reset_index())

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
    wide["waste_ratio"] = np.where(valid, wide["mean_after"] / wide["mean_before"], np.nan)
    wide["portion_cv"] = np.where(valid, wide["std_before"] / wide["mean_before"], np.nan)

    return wide.sort_values(["meal_date", "dish_name"]).reset_index(drop=True)


def _wmean(values: pd.Series, weights: pd.Series) -> float:
    m = values.notna() & weights.notna()
    if not m.any() or weights[m].sum() == 0:
        return float("nan")
    return float((values[m] * weights[m]).sum() / weights[m].sum())


def apply_calibration(ratio: pd.Series, cal: dict | None) -> pd.Series:
    if not cal:
        return ratio
    return (cal["slope"] * ratio + cal["intercept"]).clip(0, 1)


def _co_anh_truoc(daily: pd.DataFrame) -> pd.Series:
    return daily.groupby("dish_name")["waste_ratio"].transform(lambda s: s.notna().any())


def daily_value(daily: pd.DataFrame, cal: dict | None) -> pd.Series:
    return pd.Series(
        np.where(_co_anh_truoc(daily), apply_calibration(daily["waste_ratio"], cal), daily["mean_after"]),
        index=daily.index,
    )


def dish_table(daily: pd.DataFrame, taps: pd.DataFrame,
               servings: pd.DataFrame, cal: dict | None) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()

    d = daily.copy()
    d["thua"] = daily_value(d, cal)
    d["co_anh_truoc"] = _co_anh_truoc(d)

    if servings.empty:
        d["n_served"] = np.nan
    else:
        d = d.merge(servings[["meal_date", "n_served"]], on="meal_date", how="left")
    d["mau_so"] = np.fmax(d["n_served"].astype(float), d["n_after"].astype(float))

    if taps.empty:
        d["xin_them"] = 0
    else:
        tc = (taps.groupby(["meal_date", "dish_name"]).size()
                  .rename("xin_them").reset_index())
        d = d.merge(tc, on=["meal_date", "dish_name"], how="left")
        d["xin_them"] = d["xin_them"].fillna(0).astype(int)

    rows = []
    for dish, g in d.groupby("dish_name"):
        rows.append({
            "dish_name":    dish,
            "thua":         _wmean(g["thua"], g["n_after"]),
            "co_anh_truoc": bool(g["co_anh_truoc"].iloc[0]),
            "xin_them":     int(g["xin_them"].sum()),
            "tap_rate":     g["xin_them"].sum() / g["mau_so"].sum(),
            "portion_cv":   g["portion_cv"].mean(),
            "n_days":       len(g),
            "n_trays":      int(g["n_after"].sum()),
            "imputed_days": int((g["before_source"] == "imputed").sum()),
        })
    out = pd.DataFrame(rows)

    kq = [tinh_khuyen_nghi(t, r) for t, r in zip(out["thua"], out["tap_rate"])]
    out["khuyen_nghi"] = [k for k, _ in kq]
    out["ly_do"] = [l for _, l in kq]
    return out.sort_values("thua", ascending=False).reset_index(drop=True)


# Interfafce for dashboard page

def build_dashboard(start_date: str, end_date: str) -> None:
    logs = prepare(fetch_logs(start_date, end_date))
    scans = fetch_scans(start_date, end_date)
    menus = fetch_menus(start_date, end_date)
    taps = fetch_taps(start_date, end_date)
    servings = fetch_servings(start_date, end_date)
    cal = latest_calibration()

    daily = daily_table(logs, scans, menus)
    if daily.empty:
        style.empty("Chưa có dữ liệu trong khoảng ngày này",
                    "Quét khay sau bữa ở trang quét để bắt đầu.")
        return

    if not taps.empty:
        taps["dish_name"] = taps["dish_name"].map(normalize_dish)
    dishes = dish_table(daily, taps, servings, cal)
    mae = cal.get("mae") if cal else None
    so_khay = scans.loc[scans["phase"] == "after", "scan_id"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Số khay đã quét", so_khay)
    c2.metric("Tỉ lệ bỏ lại trung bình", f"{_wmean(dishes['thua'], dishes['n_trays']):.0%}")
    c3.metric("Lượt xin thêm", int(dishes["xin_them"].sum()))

    st.divider()
    st.subheader("Khuyến nghị điều chỉnh định lượng")

    show = dishes.assign(
        thua_pct=dishes["thua"] * 100,
        deu=dishes["portion_cv"].map(
            lambda v: "—" if pd.isna(v) else ("đều" if v < 0.10 else "chênh lệch")),
        ghi_chu=np.where(dishes["co_anh_truoc"], "",
                         "Thiếu ảnh trước bữa: tính theo sức chứa ngăn"),
    )
    cols = ["dish_name", "thua_pct", "xin_them", "khuyen_nghi", "ly_do", "deu", "n_days", "n_trays"]
    if not dishes["co_anh_truoc"].all():
        cols.append("ghi_chu")

    st.dataframe(
        show[cols],
        column_config={
            "dish_name": "Món",
            "thua_pct": st.column_config.ProgressColumn(
                f"Tỉ lệ bỏ lại (±{mae:.0%})" if mae is not None else "Tỉ lệ bỏ lại",
                min_value=0.0, max_value=100.0, format="%.0f%%"),
            "xin_them": "Lượt xin thêm",
            "khuyen_nghi": "Khuyến nghị",
            "ly_do": "Căn cứ",
            "deu": "Độ đều khẩu phần",
            "n_days": "Số ngày",
            "n_trays": "Số khay",
            "ghi_chu": "Ghi chú",
        },
        hide_index=True,
        width="stretch",
    )

    _chu_thich(daily, dishes, taps, servings, cal, mae, so_khay)

    st.subheader("Diễn biến theo ngày")
    trend = daily.assign(shown=daily_value(daily, cal))
    st.line_chart(trend.pivot(index="meal_date", columns="dish_name", values="shown"))

    _audit_trail(logs)


def _chu_thich(daily, dishes, taps, servings, cal, mae, so_khay) -> None:
    if mae is not None:
        st.caption(
            "Tỉ lệ bỏ lại = phần ăn được còn lại so với suất phát ra (đã trừ xương, cọng, vỏ), "
            f"hiệu chỉnh theo {cal['n']} khay cân thực tế (fit ngày {cal['fit_date']}). "
            f"±{mae:.0%} là sai số trung bình trên từng khay (MAE)."
        )
    else:
        st.warning("Chưa hiệu chỉnh với khay cân thực tế, con số chưa có biên sai số.")

    st.caption(
        f"Dựa trên {so_khay} khay. Ngưỡng khuyến nghị hiện là tạm thời. "
        "Món chỉ có 1 ngày chỉ nên tham khảo, chưa đủ để kết luận."
    )
    if (dishes["imputed_days"] > 0).any():
        st.caption("Ngày thiếu ảnh trước bữa được thay bằng trung bình các ngày khác của cùng món.")

    co_so_suat = set(servings["meal_date"]) if not servings.empty else set()
    co_tap = (set(taps.merge(daily[["meal_date", "dish_name"]], on=["meal_date", "dish_name"])["meal_date"])
              if not taps.empty else set())
    thieu = sorted(d for d in daily["meal_date"].unique() if d in co_tap and d not in co_so_suat)
    if thieu:
        ngay = ", ".join(pd.to_datetime(thieu).strftime("%d/%m"))
        st.warning(
            f"Chưa nhập số suất phục vụ ngày {ngay}. Tỉ lệ xin thêm của những ngày này đang chia "
            "cho số khay đã quét nên có thể bị thổi lên. Nhập số suất ở trang Menu."
        )


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