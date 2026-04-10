from datetime import datetime

from pydantic import BaseModel

from app.touch_panel import TouchPanelSelection


class TouchPanelActionResponse(BaseModel):
    selected_action: TouchPanelSelection


class TouchPanelActionUpdateRequest(BaseModel):
    action: TouchPanelSelection


class TouchPanelErrorCaptureRequest(BaseModel):
    message: str
    detected_at: datetime
