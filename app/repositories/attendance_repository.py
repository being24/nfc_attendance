from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.domain.enums import AttendanceStatus
from app.domain.time_utils import (
    from_unix_seconds,
    minutes_between,
    to_unix_seconds,
)
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_session import AttendanceSession
from app.models.attendance_status import AttendanceStatusModel
from app.models.break_period import BreakPeriod
from app.models.student import Student


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_event(
        self,
        student_id: int,
        event_type: str,
        occurred_at: datetime,
        source: str,
        reader_name: str | None = None,
        operator_name: str | None = None,
        memo: str | None = None,
    ) -> AttendanceEvent:
        event = AttendanceEvent(
            student_id=student_id,
            event_type=event_type,
            occurred_at=to_unix_seconds(occurred_at),
            source=source,
            reader_name=reader_name,
            operator_name=operator_name,
            memo=memo,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_status(self, student_id: int) -> AttendanceStatusModel | None:
        return self.db.get(AttendanceStatusModel, student_id)

    def upsert_status(self, student_id: int, current_status: str, last_event_id: int | None) -> AttendanceStatusModel:
        status = self.get_status(student_id)
        if status is None:
            status = AttendanceStatusModel(student_id=student_id, current_status=current_status, last_event_id=last_event_id)
            self.db.add(status)
        else:
            status.current_status = current_status
            status.last_event_id = last_event_id
        self.db.commit()
        self.db.refresh(status)
        return status

    def get_open_session(self, student_id: int) -> AttendanceSession | None:
        stmt = (
            select(AttendanceSession)
            .where(and_(AttendanceSession.student_id == student_id, AttendanceSession.left_at.is_(None)))
            .order_by(AttendanceSession.id.desc())
        )
        return self.db.scalar(stmt)

    def create_session(self, student_id: int, entered_at: datetime) -> AttendanceSession:
        session = AttendanceSession(
            student_id=student_id,
            entered_at=to_unix_seconds(entered_at),
            status="OPEN",
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def close_session(self, session: AttendanceSession, left_at: datetime, total_minutes: int) -> AttendanceSession:
        session.left_at = to_unix_seconds(left_at)
        session.total_minutes = total_minutes
        session.status = "CLOSED"
        self.db.commit()
        self.db.refresh(session)
        return session

    def start_break(self, session_id: int, started_at: datetime) -> BreakPeriod:
        bp = BreakPeriod(session_id=session_id, started_at=to_unix_seconds(started_at))
        self.db.add(bp)
        self.db.commit()
        self.db.refresh(bp)
        return bp

    def end_latest_open_break(self, session_id: int, ended_at: datetime) -> BreakPeriod | None:
        stmt = (
            select(BreakPeriod)
            .where(and_(BreakPeriod.session_id == session_id, BreakPeriod.ended_at.is_(None)))
            .order_by(BreakPeriod.id.desc())
        )
        bp = self.db.scalar(stmt)
        if bp is None:
            return None
        bp.ended_at = to_unix_seconds(ended_at)
        self.db.commit()
        self.db.refresh(bp)
        return bp

    def list_breaks(self, session_id: int) -> list[BreakPeriod]:
        stmt = select(BreakPeriod).where(BreakPeriod.session_id == session_id).order_by(BreakPeriod.id)
        return list(self.db.scalars(stmt).all())

    def sum_break_minutes(self, session_id: int, until: datetime | None = None) -> int:
        breaks = self.list_breaks(session_id)
        total = 0
        for bp in breaks:
            end_ts = bp.ended_at or (to_unix_seconds(until) if until else None)
            start_ts = bp.started_at
            end = from_unix_seconds(end_ts) if end_ts is not None else None
            start = from_unix_seconds(start_ts)
            if end is None:
                continue
            total += minutes_between(start, end)
        return total

    def list_today_events(self, target_day: date) -> list[tuple[AttendanceEvent, Student]]:
        start = datetime.combine(target_day, datetime.min.time())
        end = datetime.combine(target_day, datetime.max.time())
        start_ts = to_unix_seconds(start)
        end_ts = to_unix_seconds(end)
        stmt = (
            select(AttendanceEvent, Student)
            .join(Student, Student.id == AttendanceEvent.student_id)
            .where(and_(AttendanceEvent.occurred_at >= start_ts, AttendanceEvent.occurred_at <= end_ts))
            .order_by(AttendanceEvent.occurred_at.desc(), AttendanceEvent.id.desc())
        )
        return list(self.db.execute(stmt).all())

    def count_in_room(self) -> int:
        stmt = select(func.count(AttendanceStatusModel.student_id)).where(AttendanceStatusModel.current_status == AttendanceStatus.IN_ROOM.value)
        return int(self.db.scalar(stmt) or 0)

    def list_in_room_students(self) -> list[tuple[Student, AttendanceSession, AttendanceStatusModel]]:
        stmt = (
            select(Student, AttendanceSession, AttendanceStatusModel)
            .join(AttendanceStatusModel, AttendanceStatusModel.student_id == Student.id)
            .join(AttendanceSession, and_(AttendanceSession.student_id == Student.id, AttendanceSession.left_at.is_(None)))
            .where(AttendanceStatusModel.current_status == AttendanceStatus.IN_ROOM.value)
            .order_by(Student.name, Student.student_code, Student.id)
        )
        return list(self.db.execute(stmt).all())

    def list_students_with_open_sessions(self) -> list[tuple[Student, AttendanceSession, AttendanceStatusModel]]:
        stmt = (
            select(Student, AttendanceSession, AttendanceStatusModel)
            .join(AttendanceSession, and_(AttendanceSession.student_id == Student.id, AttendanceSession.left_at.is_(None)))
            .join(AttendanceStatusModel, AttendanceStatusModel.student_id == Student.id)
            .order_by(Student.student_code, Student.id)
        )
        return list(self.db.execute(stmt).all())

    def list_open_sessions_started_before(self, cutoff: datetime) -> list[AttendanceSession]:
        cutoff_ts = to_unix_seconds(cutoff)
        stmt = (
            select(AttendanceSession)
            .where(
                and_(
                    AttendanceSession.left_at.is_(None),
                    AttendanceSession.entered_at < cutoff_ts,
                )
            )
            .order_by(AttendanceSession.entered_at)
        )
        return list(self.db.scalars(stmt).all())

    def list_sessions_overlapping_period(self, student_id: int, start: datetime, end: datetime) -> list[AttendanceSession]:
        start_ts = to_unix_seconds(start)
        end_ts = to_unix_seconds(end)
        stmt = (
            select(AttendanceSession)
            .where(
                and_(
                    AttendanceSession.student_id == student_id,
                    AttendanceSession.entered_at < end_ts,
                    (AttendanceSession.left_at.is_(None) | (AttendanceSession.left_at > start_ts)),
                )
            )
            .order_by(AttendanceSession.entered_at)
        )
        return list(self.db.scalars(stmt).all())
