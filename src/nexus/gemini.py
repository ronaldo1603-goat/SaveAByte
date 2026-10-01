import base64
import copy

from dotenv import load_dotenv
load_dotenv()
from google import genai

from src.nexus.menu import OTHER, normalize_dish
from src.nexus.models import TrayAnalysis

client = genai.Client()

PROMPT = """
Phân tích ảnh và cho tôi biết lượng thức ăn thừa ở ngăn trong một khay. Ngăn nào trống thì không đo chứ đừng đoán.

inedible_ratio: trong phần thức ăn còn lại ở ngăn này, ước lượng tỷ lệ
là phần KHÔNG ăn được. Phần không ăn được gồm: xương gà, xương lợn,
xương cá, vỏ tôm, vỏ trứng, cuống rau muống già, lõi bắp cải,
vỏ và hạt trái cây, giấy ăn hoặc túi nilon rơi vào khay.

Anchor:
- Ngăn chỉ còn xương đã rỉa sạch thịt -> inedible_ratio = 1.0
- Ngăn còn nửa miếng thịt chưa động tới -> inedible_ratio = 0.0
- Ngăn còn thịt lẫn xương lẫn lộn -> ước lượng theo thể tích, ví dụ 0.4 """


def _prompt(menu: list[str]) -> str:
    """PROMPT gốc + thực đơn hôm nay."""
    ds = "\n".join(f"- {d}" for d in menu)
    return PROMPT + f"""

Thực đơn hôm nay:
{ds}

dish_name: chọn đúng một tên trong thực đơn trên, viết y nguyên.
Nếu ngăn có thức ăn nhưng không giống món nào trong thực đơn, ghi "{OTHER}".
Ngăn trống (has_food = false) thì ghi "{OTHER}".
Chỉ báo những ngăn bạn thực sự nhìn thấy. Món có trong thực đơn mà không thấy trên khay thì bỏ qua, KHÔNG tự thêm vào."""


def _schema(menu: list[str]) -> dict:
    """Schema của TrayAnalysis, nhưng dish_name bị khoá vào thực đơn + "khác"."""
    s = copy.deepcopy(TrayAnalysis.model_json_schema())
    s["$defs"]["Compartment"]["properties"]["dish_name"]["enum"] = [*menu, OTHER]
    return s


def read_tray(image_bytes: bytes, menu: list[str], mime: str = "image/jpeg") -> TrayAnalysis:
    if not menu:
        raise ValueError("Chưa có thực đơn. Nhập ở trang Menu trước khi quét.")

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=[
            {"type": "text", "text": _prompt(menu)},
            {"type": "image",
             "data": base64.b64encode(image_bytes).decode("utf-8"),
             "mime_type": mime},
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": _schema(menu),
        },
    )
    analysis = TrayAnalysis.model_validate_json(interaction.output_text)

    # Lưới an toàn: schema đã ép enum, nhưng vẫn kiểm lại ở phía mình
    allowed = set(menu)
    for c in analysis.compartments:
        name = normalize_dish(c.dish_name)
        c.dish_name = name if name in allowed else OTHER
    return analysis