from datetime import datetime

from pydantic import BaseModel


class AttendanceEventResponse(BaseModel):
    id: int
    student_id: int
    student_code: str
    student_name: str
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


class UnknownCardAlertResponse(BaseModel):
    card_id: str
    reader_name: str | None = None
    detected_at: datetime


class TodayAttendanceResponse(BaseModel):
    in_room: list[InRoomEntry]
    events: list[AttendanceEventResponse]
    unknown_card_alert: UnknownCardAlertResponse | None = None
