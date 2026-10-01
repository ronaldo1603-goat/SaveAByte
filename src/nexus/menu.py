import re
import unicodedata

OTHER = "khác"


def normalize_dish(name: str) -> str:
    """'  Cơm  Trắng ' (NFD/NFC bất kỳ) -> 'cơm trắng' (NFC)."""
    s = re.sub(r"\s+", " ", str(name)).strip().lower()
    return unicodedata.normalize("NFC", s)