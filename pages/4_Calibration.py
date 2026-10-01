import numpy as np
import pandas as pd
import streamlit as st

from src.nexus import style
from src.nexus.db import fetch_logs, fetch_scans, fetch_menus, save_calibration, latest_calibration
from src.nexus.dashboard import prepare, daily_table
from src.nexus.menu import normalize_dish

style.inject()
style.band("Hiệu chỉnh · đối chiếu với khay cân thực tế")

st.caption(
    "Tải file CSV số cân. Hệ thống lấy lượng phát ra trong ngày từ ảnh trước bữa, "
    "fit hệ số hiệu chỉnh và đo sai số còn lại."
)

NEED = ["meal_date", "dish_name", "vlm_after", "leftover_g", "full_portion_g"]
SO = ["vlm_after", "leftover_g", "full_portion_g"]

# Hai bên phải cùng một định nghĩa: số AI đã trừ xương thì số cân cũng phải trừ xương.
# Lệch định nghĩa thì sai số bị "fit" luôn vào hệ số và không ai phát hiện ra.
MAU_CSV = (
    "meal_date,dish_name,vlm_after,leftover_g,full_portion_g\n"
    "05/10/2026,canh bí đỏ,0.40,85,200\n"
)

up = st.file_uploader("File CSV số cân", type="csv")

with st.expander("Cách điền file CSV", expanded=up is None):
    st.markdown(
        "| Cột | Ghi gì |\n|---|---|\n"
        "| `meal_date` | Ngày quét khay, dạng 05/10/2026 hoặc 2026-10-05 |\n"
        "| `dish_name` | Tên món đúng như trong thực đơn ngày đó |\n"
        "| `vlm_after` | **Số lớn** trên ô kết quả ở trang Quét khay (phần ăn được còn lại, đã trừ xương), "
        "từ 0 đến 1. Không lấy số “còn X% ngăn” ở dòng nhỏ |\n"
        "| `leftover_g` | Gam phần **ăn được** còn lại trong ngăn. Gỡ xương, vỏ ra trước khi cân |\n"
        "| `full_portion_g` | Gam phần ăn được của **một suất đầy đủ** món đó, cân theo cùng cách |"
    )
    st.download_button("Tải file mẫu", MAU_CSV.encode("utf-8-sig"),
                       file_name="mau_hieu_chinh.csv", mime="text/csv")

if up is None:
    style.empty("Chưa có file số cân", "Điền theo hướng dẫn ở trên rồi tải file lên.")
    st.stop()

raw = pd.read_csv(up)
missing = [c for c in NEED if c not in raw.columns]
if missing:
    st.error("Thiếu cột: " + ", ".join(missing))
    st.stop()

d = raw.copy()
for c in SO:
    d[c] = pd.to_numeric(d[c], errors="coerce")       # "200g", "40%" -> NaN, bị báo ở dưới
d = d.dropna(subset=["meal_date", "dish_name"], how="all")

loi_so = (d[SO].isna().any(axis=1)
          | ~d["vlm_after"].between(0, 1)
          | (d["full_portion_g"] <= 0)
          | (d["leftover_g"] < 0)
          | (d["leftover_g"] > d["full_portion_g"]))
if loi_so.any():
    st.warning(
        f"{int(loi_so.sum())} dòng có số không hợp lệ, bị bỏ qua. vlm_after phải từ 0 đến 1 "
        "(vd 0.4, không phải 40); các cột gam chỉ ghi số; leftover_g không được lớn hơn full_portion_g."
    )
    st.dataframe(raw.loc[d.index[loi_so], NEED], hide_index=True)
d = d[~loi_so].copy()
d["dish_name"] = d["dish_name"].astype(str).map(normalize_dish)
# Đọc ISO trước (2026-10-05, Excel/Sheets hay export kiểu này), rồi mới tới kiểu Việt Nam.
# Không dùng dayfirst=True: nó đảo 2026-10-05 thành ngày 10/05.
raw_date = d["meal_date"].astype(str).str.strip()
parsed = pd.to_datetime(raw_date, format="ISO8601", errors="coerce")
for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
    parsed = parsed.fillna(pd.to_datetime(raw_date, format=fmt, errors="coerce"))

bad = parsed.isna()
if bad.any():
    st.warning(f"{int(bad.sum())} dòng có ngày không đọc được, bị bỏ qua. "
               "Ghi ngày dạng 05/10/2026 hoặc 2026-10-05.")
    st.dataframe(d.loc[bad, ["meal_date", "dish_name"]], hide_index=True)
d = d[~bad].copy()
d["meal_date"] = parsed[~bad].dt.strftime("%Y-%m-%d")

if d.empty:
    st.error("Không còn dòng nào dùng được. Kiểm tra lại cột meal_date và các cột số.")
    st.stop()

lo, hi = d["meal_date"].min(), d["meal_date"].max()
daily = daily_table(prepare(fetch_logs(lo, hi)), fetch_scans(lo, hi), fetch_menus(lo, hi))

if daily.empty:
    st.error("Chưa có ảnh khay sau bữa nào trên hệ thống trong những ngày này.")
    st.stop()

d = d.merge(daily[["meal_date", "dish_name", "mean_before"]],
            on=["meal_date", "dish_name"], how="left")

lech = d[~(d["mean_before"] > 0)]
if not lech.empty:
    hop_le = (daily.groupby("meal_date")["dish_name"]
              .agg(lambda s: ", ".join(sorted(s)))
              .rename("tên hợp lệ").reset_index())
    st.warning(
        f"{len(lech)} dòng bị bỏ qua: tên món không có trong thực đơn ngày đó, "
        "hoặc ngày đó thiếu ảnh trước bữa. Sửa tên món trong CSV theo cột “tên hợp lệ”."
    )
    st.dataframe(lech[["meal_date", "dish_name"]].merge(hop_le, on="meal_date", how="left"),
                 hide_index=True)
d = d[d["mean_before"] > 0]

if len(d) < 8:
    st.info(f"Dùng được {len(d)} khay. Cần tối thiểu 8 để fit.")
    st.stop()

x = (d["vlm_after"] / d["mean_before"]).to_numpy(dtype=float)
y = (d["leftover_g"] / d["full_portion_g"]).to_numpy(dtype=float)

if np.ptp(x) == 0:
    st.error("Mọi khay có cùng giá trị AI — không fit được. Cần khay rải đều từ sạch đến gần nguyên.")
    st.stop()

slope, intercept = np.polyfit(x, y, 1)
y_hat = slope * x + intercept

errs = []
for i in range(len(x)):
    m = np.arange(len(x)) != i
    s_i, b_i = np.polyfit(x[m], y[m], 1)
    errs.append(abs(s_i * x[i] + b_i - y[i]))
mae = float(np.mean(errs))

bias_before = float(np.mean(x - y))
spearman    = float(pd.Series(x).rank().corr(pd.Series(y).rank()))   # không cần scipy
ss_res      = float(np.sum((y - y_hat) ** 2))
ss_tot      = float(np.sum((y - y.mean()) ** 2))
r2          = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spearman", f"{spearman:.2f}")
c2.metric("MAE sau hiệu chỉnh", f"{mae:.3f}")
c3.metric("Bias trước hiệu chỉnh", f"{bias_before:+.3f}")
c4.metric("n", len(d))

st.scatter_chart(pd.DataFrame({"AI ước lượng": x, "Cân thực tế": y}),
                 x="AI ước lượng", y="Cân thực tế")

st.write(f"`true_hat = {slope:.3f} × vlm + {intercept:.3f}`  —  R² = {r2:.2f}")

if st.button("Lưu hệ số"):
    save_calibration(float(slope), float(intercept), int(len(d)),
                     mae, bias_before, spearman)
    st.success("Đã lưu.")

st.divider()
cur = latest_calibration()
if cur:
    st.caption(
        f"Hệ số đang dùng: true = {cur['slope']:.3f} × AI + {cur['intercept']:.3f} · "
        f"MAE {cur['mae']:.3f} · n = {cur['n']} · fit ngày {cur['fit_date']}"
    )