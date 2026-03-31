from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import AttendanceAction, AttendanceStatus


class PendingTouch(BaseModel):
    touch_token: str
    student_id: int
    card_id: str
    reader_name: str | None
    detected_at: datetime
    current_status: AttendanceStatus
    allowed_actions: list[AttendanceAction]
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
