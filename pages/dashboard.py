# pages/3_Dashboard.py
from datetime import date, timedelta

import streamlit as st

from src.nexus.dashboard import build_dashboard, build_weekly

from src.nexus import style
style.inject()

today = date.today()
col1, col2 = st.columns(2)
start = col1.date_input("From", today - timedelta(days=7))
end = col2.date_input("To", today)

style.band(f"Kitchen dashboard · {start:%d/%m} – {end:%d/%m}")

build_dashboard(start.isoformat(), end.isoformat())

st.divider()
build_weekly(start.isoformat(), end.isoformat())