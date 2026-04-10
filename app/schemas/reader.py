from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import AttendanceAction, AttendanceStatus


class ReaderTouchRequest(BaseModel):
    card_id: str
    reader_name: str | None = None
    detected_at: datetime


class ReaderTouchResponse(BaseModel):
    touch_token: str
    student_id: int
    student_name: str
    current_status: AttendanceStatus
    allowed_actions: list[AttendanceAction]
    preferred_action: AttendanceAction | None = None
    expires_at: datetime


class ReaderTouchConfirmRequest(BaseModel):
    action: AttendanceAction
    now: datetime | None = None


class ReaderTouchConfirmResponse(BaseModel):
    student_id: int
    next_status: AttendanceStatus
    event_id: int
    lock_alert_required: bool
