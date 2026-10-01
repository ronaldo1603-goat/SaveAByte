# pages/3_Dashboard.py
from datetime import timedelta

import streamlit as st

from src.nexus import style
from src.nexus.clock import today_vn
from src.nexus.dashboard import build_dashboard

style.inject()

# Giữ chỗ để band nằm trên cùng, dù nội dung band phải đợi biết khoảng ngày mới viết được
header = st.container()

today = today_vn()
col1, col2 = st.columns(2)
start = col1.date_input("Từ ngày", today - timedelta(days=7), format="DD/MM/YYYY")
end = col2.date_input("Đến ngày", today, format="DD/MM/YYYY")

with header:
    style.band(f"Bảng theo dõi cho bếp · {start:%d/%m} – {end:%d/%m}")

if start > end:
    st.error("Ngày bắt đầu đang sau ngày kết thúc. Chọn lại khoảng ngày.")
    st.stop()

build_dashboard(start.isoformat(), end.isoformat())