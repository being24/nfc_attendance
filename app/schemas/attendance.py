from datetime import datetime

from pydantic import BaseModel


class AttendanceEventResponse(BaseModel):
    id: int
    student_id: int
    event_type: str
    occurred_at: datetime
    source: str


class InRoomEntry(BaseModel):
    student_id: int
    student_code: str
    name: str
    entered_at: datetime
    current_status: str
    cumulative_minutes: int


class TodayAttendanceResponse(BaseModel):
    in_room: list[InRoomEntry]
    events: list[AttendanceEventResponse]
