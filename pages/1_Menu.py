from datetime import timedelta

import streamlit as st

from src.nexus import style
from src.nexus.clock import today_vn
from src.nexus.db import (fetch_known_dishes, fetch_menu, fetch_menus, fetch_serving,
                         fetch_servings, save_menu, save_serving)

style.inject()
style.band("Thực đơn · nhập trước bữa ăn")

THU = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]

# Thông báo từ lần bấm Lưu trước (st.rerun xoá mọi thứ đã vẽ, nên phải giữ qua session_state)
if msg := st.session_state.pop("menu_flash", None):
    st.success(msg)

day = st.date_input("Ngày", value=today_vn(), format="DD/MM/YYYY")
day_str = day.isoformat()

current = fetch_menu(day_str)
options = list(dict.fromkeys(current + fetch_known_dishes()))
key = f"menu_{day_str}"   # mỗi ngày một widget riêng -> đổi ngày là nạp đúng thực đơn ngày đó

chosen = st.multiselect(
    "Các món",
    options=options,
    default=current,
    accept_new_options=True,
    placeholder="Gõ để tìm món đã có. Món mới: gõ tên rồi Enter",
    key=key,
)
st.caption("Ưu tiên chọn món có sẵn trong gợi ý để tên món giữ nguyên qua các tuần. "
           "AI chỉ được gán tên món trong danh sách này khi đọc khay.")

key_suat = f"servings_{day_str}"
so_suat = st.number_input(
    "Số suất phục vụ", min_value=0, step=10, value=fetch_serving(day_str) or 0, key=key_suat,
    help="Tổng số suất bếp phát ra trong bữa. Dùng làm mẫu số cho tỉ lệ xin thêm trên dashboard.",
)

if st.button("Lưu thực đơn", type="primary"):
    if not chosen:
        st.error("Thực đơn đang trống. Thêm ít nhất 1 món rồi lưu.")
    else:
        saved = save_menu(day_str, chosen)
        if so_suat > 0:
            save_serving(day_str, int(so_suat))
        st.session_state.pop(key, None)   # nạp lại từ DB với tên đã chuẩn hoá
        st.session_state.pop(key_suat, None)
        suat = f", {int(so_suat)} suất" if so_suat > 0 else ", chưa nhập số suất"
        st.session_state["menu_flash"] = f"Đã lưu thực đơn {THU[day.weekday()]} {day:%d/%m}: {len(saved)} món{suat}."
        st.rerun()

# ---- Tổng quan tuần: để bếp thấy ngày nào chưa nhập ----
st.markdown("## Tuần này")
monday = day - timedelta(days=day.weekday())
week = fetch_menus(monday.isoformat(), (monday + timedelta(days=6)).isoformat())
by_day = {} if week.empty else week.groupby("meal_date")["dish_name"].apply(list).to_dict()
sv = fetch_servings(monday.isoformat(), (monday + timedelta(days=6)).isoformat())
suat_by_day = {} if sv.empty else dict(zip(sv["meal_date"], sv["n_served"]))

rows = []
for i in range(7):
    d = monday + timedelta(days=i)
    dishes = by_day.get(d.isoformat(), [])
    rows.append({"Ngày": f"{THU[i]} {d:%d/%m}",
                 "Món": ", ".join(dishes) if dishes else "chưa nhập",
                 "Số suất": str(suat_by_day.get(d.isoformat(), "—"))})
st.dataframe(rows, hide_index=True)