# pages/2_Tap_Counter.py
import streamlit as st

from src.nexus.clock import today_vn
from src.nexus.db import fetch_menu, log_tap

from src.nexus import style
style.inject()

today_d = today_vn()
today = today_d.isoformat()

style.band("Đếm lượt xin thêm · " + today_d.strftime("%d/%m"))

DISHES = fetch_menu(today)   # lấy từ trang Menu, không còn list cứng
if not DISHES:
    style.empty("Chưa có thực đơn hôm nay",
                "Vào trang Menu nhập các món của bữa này trước.")
    st.stop()

# Sang ngày mới thì bộ đếm hiển thị về 0 (máy để mở qua đêm vẫn đúng)
if st.session_state.get("taps_date") != today:
    st.session_state.taps = {}
    st.session_state.taps_date = today

cols = st.columns(len(DISHES))

for col, dish in zip(cols, DISHES):
    with col:
        if st.button(dish.capitalize(), key=f"tap_{dish}", width="stretch"):
            try:
                log_tap(dish, today)
            except Exception:
                st.error("Chưa ghi được lượt này. Kiểm tra mạng rồi bấm lại.")
            else:   # chỉ tăng số hiển thị khi đã ghi được vào DB
                st.session_state.taps[dish] = st.session_state.taps.get(dish, 0) + 1
        st.metric(label=dish.capitalize(), value=st.session_state.taps.get(dish, 0))

st.divider()
if st.button("Đặt lại số trên màn hình",
             help="Chỉ đưa số hiển thị về 0. Các lượt đã ghi vẫn giữ nguyên trong dữ liệu."):
    st.session_state.taps = {}
    st.rerun()