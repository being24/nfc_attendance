from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.time_utils import now_ts


class AttendanceStatusModel(Base):
    __tablename__ = "attendance_status"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    current_status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now_ts, onupdate=now_ts, nullable=False)
