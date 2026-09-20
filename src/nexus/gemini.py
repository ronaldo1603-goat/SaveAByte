from dotenv import load_dotenv
load_dotenv()
from google import genai
import base64
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.resolve()))
from models import TrayAnalysis

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

def read_tray(image_bytes: bytes, mime: str = "image/jpeg") -> TrayAnalysis:
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=[
            {"type": "text", "text": PROMPT},
            {"type": "image",
             "data": base64.b64encode(image_bytes).decode("utf-8"),
             "mime_type": mime},
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TrayAnalysis.model_json_schema(),
        },
    )
    return TrayAnalysis.model_validate_json(interaction.output_text)