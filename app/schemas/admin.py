from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import AttendanceAction


class CorrectionRequest(BaseModel):
    student_id: int
    action: AttendanceAction
    occurred_at: datetime
    operator_name: str | None = None
    memo: str | None = None
    reader_name: str | None = None
