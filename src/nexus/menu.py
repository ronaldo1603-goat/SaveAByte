"""Chuẩn hoá tên món. Mọi chỗ ghi tên món vào DB đều đi qua normalize_dish."""
import re
import unicodedata

# Giá trị Gemini được phép trả khi thấy món KHÔNG có trong thực đơn hôm đó
OTHER = "khác"


def normalize_dish(name: str) -> str:
    """'  Cơm  Trắng ' (NFD/NFC bất kỳ) -> 'cơm trắng' (NFC)."""
    s = re.sub(r"\s+", " ", str(name)).strip().lower()
    return unicodedata.normalize("NFC", s)