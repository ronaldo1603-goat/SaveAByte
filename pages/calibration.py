import numpy as np
import pandas as pd
import streamlit as st

from src.nexus import style
from src.nexus.db import fetch_logs, save_calibration, latest_calibration
from src.nexus.dashboard import prepare, daily_table

style.inject()
style.band("Hiệu chỉnh · đối chiếu với khay cân thực tế")

st.caption(
    "Tải file CSV số cân. Hệ thống lấy lượng phát ra trong ngày từ ảnh trước bữa, "
    "fit hệ số hiệu chỉnh và đo sai số còn lại."
)

NEED = ["meal_date", "dish_name", "vlm_after", "leftover_g", "full_portion_g"]

up = st.file_uploader("File CSV số cân", type="csv")
if up is None:
    style.empty("Chưa có file số cân", "Cột bắt buộc: " + ", ".join(NEED))
    st.stop()

raw = pd.read_csv(up)
missing = [c for c in NEED if c not in raw.columns]
if missing:
    st.error("Thiếu cột: " + ", ".join(missing))
    st.stop()

d = raw.dropna(subset=NEED).copy()
d = d[d["full_portion_g"] > 0]
d["dish_name"] = d["dish_name"].astype(str).str.strip().str.lower()
d["meal_date"] = (pd.to_datetime(d["meal_date"], dayfirst=True, format="mixed")
                  .dt.strftime("%Y-%m-%d"))

daily = daily_table(prepare(fetch_logs(d["meal_date"].min(), d["meal_date"].max())))
if daily.empty:
    st.error("Chưa có ảnh khay sau bữa nào trên hệ thống trong những ngày này.")
    st.stop()

d = d.merge(daily[["meal_date", "dish_name", "mean_before"]],
            on=["meal_date", "dish_name"], how="left")

lech = d[~(d["mean_before"] > 0)]
if not lech.empty:
    st.warning(
        f"{len(lech)} dòng không khớp (ngày, tên món) với dữ liệu quét — bị bỏ qua. "
        "Sửa tên món trong CSV cho giống hệt tên AI trả về."
    )
    st.dataframe(lech[["meal_date", "dish_name"]], hide_index=True)
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