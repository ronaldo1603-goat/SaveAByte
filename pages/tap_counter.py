# pages/2_Tap_Counter.py
from datetime import date

import streamlit as st

from src.nexus.db import log_tap

from src.nexus import style
style.inject()

DISHES = [
    "Cơm trắng",
    "Cá basa rang muối",
    "Thịt lợn rim tiêu",
    "Đậu trắng sốt Tứ Xuyên",
]

today = date.today().isoformat()

style.band("Extra portions count · " + date.today().strftime("%d/%m"))

if "taps" not in st.session_state:
    st.session_state.taps = {d: 0 for d in DISHES}

cols = st.columns(len(DISHES))

for col, dish in zip(cols, DISHES):
    with col:
        if st.button(dish, use_container_width=True):
            log_tap(dish, today)
            st.session_state.taps[dish] += 1
        st.metric(label=dish, value=st.session_state.taps[dish])

st.divider()
if st.button("Reset display counter"):
    st.session_state.taps = {d: 0 for d in DISHES}
    st.rerun()