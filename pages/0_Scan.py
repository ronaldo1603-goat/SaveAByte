import io
import uuid

import streamlit as st
from PIL import Image, ImageOps
from pydantic import ValidationError

from src.nexus import style
from src.nexus.gemini import read_tray
from src.nexus.db import upload_tray_image, save_scan, fetch_menu
from src.nexus.menu import OTHER
from src.nexus.clock import today_vn

MAX_SIDE = 1536   # px, cạnh dài sau khi thu nhỏ


def chuan_hoa_anh(raw: bytes) -> bytes:
    """Xoay đúng chiều theo EXIF, thu cạnh dài về MAX_SIDE, lưu lại thành JPEG."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def het_quota(e: Exception) -> bool:
    s = str(e)
    return getattr(e, "code", None) == 429 or "429" in s or "RESOURCE_EXHAUSTED" in s


def bao_loi(tieu_de: str, goi_y: str, e: Exception) -> None:
    """Thay traceback đỏ bằng thông báo dễ hiểu; chi tiết kỹ thuật vẫn xem được."""
    style.empty(tieu_de, goi_y)
    with st.expander("Chi tiết kỹ thuật"):
        st.code(f"{type(e).__name__}: {e}")
    st.stop()


style.inject()
style.band("Quét khay · trạm trả khay")

today = today_vn().isoformat()
try:
    menu = fetch_menu(today)
except Exception as e:
    bao_loi("Không kết nối được cơ sở dữ liệu", "Kiểm tra mạng rồi tải lại trang.", e)
if not menu:
    style.empty("Chưa có thực đơn hôm nay",
                "Vào trang Menu nhập các món của bữa này, rồi quay lại quét khay.")
    st.stop()
st.caption("Thực đơn hôm nay: " + ", ".join(menu))

st.markdown(
    "Chụp khay từ trên xuống, lấy trọn các ngăn, tránh bóng tay che mặt thức ăn."
)

phase_label = st.radio(
    "Loại ảnh",
    ["Sau bữa (khay trả về)", "Trước bữa (khay vừa phát)"],
    horizontal=True,
)
phase = "before" if phase_label.startswith("Trước") else "after"

uploaded = st.file_uploader("Ảnh khay", type=["jpg", "jpeg", "png"])

if uploaded is None:
    style.empty(
        "Chưa có ảnh khay",
        "Tải một ảnh lên để hệ thống ước lượng lượng thức ăn còn lại trong từng ngăn.",
    )
    st.stop()

try:
    image_bytes = chuan_hoa_anh(uploaded.getvalue())
except Exception as e:
    bao_loi("Không đọc được ảnh", "File có thể bị hỏng. Chụp lại hoặc chọn ảnh khác.", e)
st.image(image_bytes, width=380)   # hiện đúng ảnh AI sẽ nhận

# Ghi rõ chế độ trên nút, để khó bấm nhầm khi quên chuyển chế độ
nhan_nut = "Phân tích khay trước bữa" if phase == "before" else "Phân tích khay sau bữa"
if not st.button(nhan_nut, type="primary", width="stretch"):
    st.stop()

scan_id = str(uuid.uuid4())

try:
    with st.spinner("Đang đọc ảnh..."):
        analysis = read_tray(image_bytes, menu)   # ảnh đã là JPEG nên dùng mime mặc định
except ValidationError as e:
    bao_loi("AI trả kết quả không hợp lệ",
            "Bấm “Phân tích khay” lần nữa. Lỗi này thường không lặp lại.", e)
except Exception as e:
    if het_quota(e):
        bao_loi("Hết lượt gọi AI",
                "Gói miễn phí của Gemini đã dùng hết quota. Thử lại sau, hoặc đổi sang API key khác.", e)
    bao_loi("Không gọi được AI", "Kiểm tra kết nối mạng rồi bấm “Phân tích khay” lần nữa.", e)

co_do_an = [c for c in analysis.compartments if c.has_food]
ngoai_menu = [c for c in co_do_an if c.dish_name == OTHER]

# Khay TRƯỚC bữa mà trống là ảnh hỏng -> không lưu
if phase == "before" and not co_do_an:
    style.empty("Không thấy thức ăn trên khay trước bữa",
                "Ảnh chưa lấy trọn các ngăn? Chụp lại từ trên xuống.")
    st.stop()

try:
    with st.spinner("Đang lưu..."):
        path = upload_tray_image(image_bytes, scan_id, today)
        save_scan(scan_id, path, analysis, today, phase=phase)
except Exception as e:
    bao_loi("Chưa lưu được khay này",
            "Mất kết nối tới cơ sở dữ liệu. Kiểm tra mạng rồi bấm “Phân tích khay” lần nữa.", e)

st.markdown("## Kết quả")

if not co_do_an:
    # Khay SAU bữa trống = ăn sạch -> vẫn được đếm, hiện 1 ô 0% cho cả khay
    style.wells([{"label": "Cả khay", "value": 0.0,
                  "note": "không còn thức ăn · tính 0% cho mọi món"}])
    st.success("Đã lưu: khay ăn sạch.")
else:
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
    st.success(f"Đã lưu {len(co_do_an)} ngăn.")

if ngoai_menu:
    st.warning(
        f"{len(ngoai_menu)} ngăn có món không khớp thực đơn, đã lưu với tên “{OTHER}” "
        "và không tính vào món nào. Nếu thực đơn nhập thiếu món, sửa ở trang Menu "
        "để các khay sau được tính đúng."
    )

with st.expander("Dữ liệu thô (để kiểm tra)"):
    st.json(analysis.model_dump())