from datetime import date, datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))

def today_vn() -> date:
    return datetime.now(VN).date()