import uuid
from datetime import date

import streamlit as st

from src.nexus import style
from src.nexus.gemini import read_tray
from src.nexus.db import upload_tray_image, save_scan

st.set_page_config(
    page_title="Vừa Đủ · Quét khay",
    page_icon="◫",
    layout="centered",
)

style.inject()
style.band("Quét khay · trạm trả khay")

st.markdown(
    "Chụp khay từ trên xuống, lấy trọn các ngăn, tránh bóng tay che mặt thức ăn."
)

uploaded = st.file_uploader("Ảnh khay", type=["jpg", "jpeg", "png"])

if uploaded is None:
    style.empty(
        "Chưa có ảnh khay",
        "Tải một ảnh lên để hệ thống ước lượng lượng thức ăn còn lại trong từng ngăn.",
    )
    st.stop()

image_bytes = uploaded.getvalue()
st.image(image_bytes, width=380)

phase_label = st.radio(
    "Loại ảnh",
    ["Sau bữa (khay trả về)", "Trước bữa (khay vừa phát)"],
    horizontal=True,
)
phase = "before" if phase_label.startswith("Trước") else "after"

if not st.button("Phân tích khay", use_container_width=True):
    st.stop()

scan_id = str(uuid.uuid4())
today = date.today().isoformat()

with st.spinner("Đang đọc ảnh..."):
    analysis = read_tray(image_bytes)

co_do_an = [c for c in analysis.compartments if c.has_food]

if not co_do_an:
    style.empty(
        "Không thấy ngăn nào còn thức ăn",
        "Khay đã ăn sạch, hoặc ảnh chưa lấy trọn các ngăn. Thử chụp lại từ trên xuống.",
    )
    st.stop()

st.markdown("## Kết quả")

style.wells([
    {
        "label": c.dish_name.capitalize(),
        "value": c.fill_fraction * (1 - c.inedible_ratio),
        "note": (f"còn {c.fill_fraction:.0%} ngăn · "
                 f"{c.inedible_ratio:.0%} không ăn được"),
    }
    for c in co_do_an
])

st.caption(
    "Con số lớn là phần thức ăn **ăn được** còn lại, tính theo sức chứa ngăn khay. "
    "Chưa hiệu chỉnh với khay cân thực tế."
)

with st.spinner("Đang lưu..."):
    path = upload_tray_image(image_bytes, scan_id, today)
    save_scan(scan_id, path, analysis, today, phase=phase)

st.success(f"Đã lưu {len(co_do_an)} ngăn.")

with st.expander("Dữ liệu thô (để kiểm tra)"):
    st.json(analysis.model_dump())
