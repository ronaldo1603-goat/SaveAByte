import streamlit as st

st.set_page_config(page_icon="◫", layout="centered")

# Tên trang, icon và thứ tự trong sidebar khai báo ở đây (thay cho tên file trong pages/)
pg = st.navigation({
    "Hằng ngày": [
        st.Page("pages/1_Menu.py", title="Thực đơn", icon=":material/restaurant_menu:"),
        st.Page("pages/0_Scan.py", title="Quét khay", icon=":material/photo_camera:", default=True),
        st.Page("pages/2_Tap_Counter.py", title="Đếm lượt xin thêm", icon=":material/touch_app:"),
    ],
    "Phân tích": [
        st.Page("pages/3_Dashboard.py", title="Bảng theo dõi", icon=":material/monitoring:"),
        st.Page("pages/4_Calibration.py", title="Hiệu chỉnh", icon=":material/tune:"),
    ],
})
pg.run()