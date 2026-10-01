"""Ngày giờ theo giờ Việt Nam. Server Streamlit Cloud chạy giờ UTC (chậm 7 tiếng)."""
from datetime import date, datetime, timedelta, timezone

# Việt Nam không đổi giờ mùa hè, nên offset cố định +7 là chính xác quanh năm
VN = timezone(timedelta(hours=7))


def today_vn() -> date:
    return datetime.now(VN).date()