from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class LocationUpdate(BaseModel):
    """
    資料定義
    """
    driver_id: str = Field(..., min_length=1, description="司機的id")
    latitude: float = Field(..., ge=-90, le=90, description="緯度")
    longitude: float = Field(..., ge=-180, le=180, description="經度")
    status: Literal['online', 'busy', 'offline'] = 'online'
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('latitude', 'longitude')
    @classmethod
    def validate_precision(cls, v: float) -> float:
        return round(v, 6) # 限制小數點後六位
