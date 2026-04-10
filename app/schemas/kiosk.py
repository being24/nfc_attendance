from datetime import datetime

from pydantic import BaseModel

from app.kiosk import KioskMode


class KioskModeResponse(BaseModel):
    mode: KioskMode


class CardCaptureResponse(BaseModel):
    card_id: str
    reader_name: str | None = None
    detected_at: datetime
