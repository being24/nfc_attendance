from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    student_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    card_id: str = Field(min_length=1)
    note: str | None = None


class StudentUpdate(BaseModel):
    name: str | None = None
    card_id: str | None = None
    note: str | None = None
    is_active: bool | None = None


class StudentResponse(BaseModel):
    id: int
    student_code: str
    name: str
    card_id: str
    is_active: bool
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
