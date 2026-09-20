from pydantic import BaseModel, Field
from typing import List

class Compartment(BaseModel):
    dish_name: str
    has_food: bool = Field(description="True nếu ngăn có đồ ăn, False nếu ngăn trống")
    fill_fraction: float = Field(
        ge=0.0, le=1.0,
        description="Lượng thức ăn còn lại trong một khay từ 0 đến 1 với 0=hết sạch và 1=còn nguyên.",
        examples=[0.35, 0.75, 0.25]
    )
    inedible_ratio: float = Field(ge=0.0, le=1.0)

class TrayAnalysis(BaseModel):
    compartments: List[Compartment]