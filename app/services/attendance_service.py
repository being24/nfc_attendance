from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.enums import AttendanceAction, AttendanceStatus
from app.domain.pending_touch import PendingTouch
from app.domain.state_machine import InvalidTransitionError, get_allowed_actions, next_state
from app.domain.time_utils import ensure_jst, from_unix_seconds, minutes_between, now_jst
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.unknown_card_repository import UnknownCardRepository
from app.realtime import attendance_event_broker
from app.models.attendance_session import AttendanceSession
from app.models.student import Student
from app.schemas.attendance import AttendanceEventResponse, InRoomEntry, TodayAttendanceResponse
from app.schemas.attendance import UnknownCardAlertResponse
from app.schemas.reader import ReaderTouchConfirmResponse, ReaderTouchResponse
from app.services.audit_service import AuditService
from app.services.exceptions import (
    InactiveStudentError,
    InvalidActionError,
    TouchTokenExpiredError,
    TouchTokenNotFoundError,
    UnknownCardError,
)


class AttendanceService:
    PENDING_TTL_SECONDS = 20
    UNKNOWN_CARD_ALERT_WINDOW_SECONDS = 30
    _shared_pending_touches: dict[str, PendingTouch] = {}

    def __init__(self, db: Session):
        self.db = db
        self.student_repo = StudentRepository(db)
        self.att_repo = AttendanceRepository(db)
        self.unknown_repo = UnknownCardRepository(db)
        self.audit_service = AuditService(db)
        self._pending_touches = self._shared_pending_touches

    def _get_current_status(self, student_id: int) -> AttendanceStatus:
        status_model = self.att_repo.get_status(student_id)
        if status_model is None:
            return AttendanceStatus.OUTSIDE
        return AttendanceStatus(status_model.current_status)

    def prepare_touch(self, card_id: str, reader_name: str | None, detected_at: datetime) -> ReaderTouchResponse:
        student = self.student_repo.get_by_card_id(card_id)
        if student is None:
            self.unknown_repo.create(card_id=card_id, reader_name=reader_name, detected_at=detected_at)
            attendance_event_broker.publish()
            raise UnknownCardError("未登録のカードです")
        if not student.is_active:
            raise InactiveStudentError("非アクティブな学生です")

        current_status = self._get_current_status(student.id)
        allowed_actions = get_allowed_actions(current_status)

        token = str(uuid4())
        pending = PendingTouch(
            touch_token=token,
            student_id=student.id,
            card_id=student.card_id,
            reader_name=reader_name,
            detected_at=detected_at,
            current_status=current_status,
            allowed_actions=allowed_actions,
            expires_at=detected_at + timedelta(seconds=self.PENDING_TTL_SECONDS),
        )
        self._pending_touches[token] = pending

        return ReaderTouchResponse(
            touch_token=token,
            student_id=student.id,
            student_name=student.name,
            current_status=current_status,
            allowed_actions=allowed_actions,
            expires_at=pending.expires_at,
        )

    def confirm_touch(self, touch_token: str, action: AttendanceAction, now: datetime | None = None) -> ReaderTouchConfirmResponse:
        pending = self._pending_touches.get(touch_token)
        if pending is None:
            raise TouchTokenNotFoundError("タッチトークンが見つかりません")

        now = now or now_jst()
        if pending.is_expired(now):
            self._pending_touches.pop(touch_token, None)
            raise TouchTokenExpiredError("タッチトークンの有効期限が切れています")

        if action not in pending.allowed_actions:
            raise InvalidActionError("許可されていない操作です")

        try:
            new_status = next_state(pending.current_status, action)
        except InvalidTransitionError as e:
            raise InvalidActionError(str(e)) from e

        event = self.att_repo.add_event(
            student_id=pending.student_id,
            event_type=action.value,
            occurred_at=now,
            source="reader",
            reader_name=pending.reader_name,
        )
        self.att_repo.upsert_status(
            student_id=pending.student_id,
            current_status=new_status.value,
            last_event_id=event.id,
        )

        lock_alert_required = False
        open_session = self.att_repo.get_open_session(pending.student_id)

        if pending.current_status == AttendanceStatus.OUTSIDE and action == AttendanceAction.ENTER:
            self.att_repo.create_session(student_id=pending.student_id, entered_at=now)
        elif pending.current_status == AttendanceStatus.IN_ROOM and action == AttendanceAction.LEAVE_TEMP:
            if open_session:
                self.att_repo.start_break(session_id=open_session.id, started_at=now)
        elif pending.current_status == AttendanceStatus.OUT_ON_BREAK and action == AttendanceAction.RETURN:
            if open_session:
                self.att_repo.end_latest_open_break(session_id=open_session.id, ended_at=now)
        elif pending.current_status == AttendanceStatus.IN_ROOM and action == AttendanceAction.LEAVE_FINAL:
            if open_session:
                total_minutes = self._compute_net_minutes(
                    from_unix_seconds(open_session.entered_at),
                    now,
                    open_session.id,
                )
                self.att_repo.close_session(open_session, left_at=now, total_minutes=total_minutes)
            lock_alert_required = self.att_repo.count_in_room() == 0
            if lock_alert_required:
                self.audit_service.log(
                    actor_type="system",
                    action="LOCK_ALERT",
                    target_type="student",
                    target_id=pending.student_id,
                    detail={"message": "在室者が0人になりました。施錠してください"},
                )

        self._pending_touches.pop(touch_token, None)
        attendance_event_broker.publish()

        return ReaderTouchConfirmResponse(
            student_id=pending.student_id,
            next_status=new_status,
            event_id=event.id,
            lock_alert_required=lock_alert_required,
        )

    def _compute_net_minutes(self, entered_at: datetime, left_at: datetime, session_id: int) -> int:
        entered = ensure_jst(entered_at)
        left = ensure_jst(left_at)
        gross = minutes_between(entered, left)
        break_minutes = self.att_repo.sum_break_minutes(session_id=session_id, until=left)
        return max(0, gross - break_minutes)

    def _compute_net_minutes_for_period(
        self,
        session: AttendanceSession,
        period_start: datetime,
        period_end: datetime,
        now: datetime,
    ) -> int:
        session_start = from_unix_seconds(session.entered_at)
        session_end = from_unix_seconds(session.left_at) if session.left_at is not None else ensure_jst(now)
        overlap_start = max(session_start, ensure_jst(period_start))
        overlap_end = min(session_end, ensure_jst(period_end))
        if overlap_end <= overlap_start:
            return 0

        gross = minutes_between(overlap_start, overlap_end)
        break_minutes = 0
        for bp in self.att_repo.list_breaks(session.id):
            bp_start = from_unix_seconds(bp.started_at)
            bp_end = from_unix_seconds(bp.ended_at) if bp.ended_at is not None else session_end
            b_start = max(bp_start, overlap_start)
            b_end = min(bp_end, overlap_end)
            if b_end > b_start:
                break_minutes += minutes_between(b_start, b_end)
        return max(0, gross - break_minutes)

    def current_term_bounds(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        base = ensure_jst(now or now_jst())
        y = base.year
        m = base.month
        if 4 <= m <= 9:
            return (
                base.replace(year=y, month=4, day=1, hour=0, minute=0, second=0, microsecond=0),
                base.replace(year=y, month=10, day=1, hour=0, minute=0, second=0, microsecond=0),
            )
        if m >= 10:
            return (
                base.replace(year=y, month=10, day=1, hour=0, minute=0, second=0, microsecond=0),
                base.replace(year=y + 1, month=4, day=1, hour=0, minute=0, second=0, microsecond=0),
            )
        return (
            base.replace(year=y - 1, month=10, day=1, hour=0, minute=0, second=0, microsecond=0),
            base.replace(year=y, month=4, day=1, hour=0, minute=0, second=0, microsecond=0),
        )

    def get_current_term_total_minutes_by_card(
        self,
        card_id: str,
        now: datetime | None = None,
    ) -> tuple[Student, int, datetime, datetime]:
        student = self.student_repo.get_by_card_id(card_id)
        if student is None:
            raise UnknownCardError("未登録のカードです")

        current = ensure_jst(now or now_jst())
        start, end = self.current_term_bounds(current)
        sessions = self.att_repo.list_sessions_overlapping_period(student.id, start, end)
        total = sum(self._compute_net_minutes_for_period(s, start, end, current) for s in sessions)
        return student, total, start, min(end, current)

    def compute_9_to_17_minutes(self, entered_at: datetime, left_at: datetime, session_id: int) -> int:
        entered = ensure_jst(entered_at)
        left = ensure_jst(left_at)
        if left <= entered:
            return 0

        business_start = entered.replace(hour=9, minute=0, second=0, microsecond=0)
        business_end = entered.replace(hour=17, minute=0, second=0, microsecond=0)
        start = max(entered, business_start)
        end = min(left, business_end)
        if end <= start:
            return 0

        business_minutes = minutes_between(start, end)

        break_minutes_in_business = 0
        for bp in self.att_repo.list_breaks(session_id):
            bp_start = from_unix_seconds(bp.started_at)
            bp_end = from_unix_seconds(bp.ended_at) if bp.ended_at is not None else left
            overlap_start = max(bp_start, start)
            overlap_end = min(bp_end, end)
            if overlap_end > overlap_start:
                break_minutes_in_business += minutes_between(overlap_start, overlap_end)

        return max(0, business_minutes - break_minutes_in_business)

    def get_today_attendance(self) -> TodayAttendanceResponse:
        now = now_jst()
        rows = self.att_repo.list_in_room_students()
        in_room: list[InRoomEntry] = []
        for student, session, status in rows:
            entered_at_dt = from_unix_seconds(session.entered_at)
            cumulative = self._compute_net_minutes(entered_at_dt, now, session.id)
            in_room.append(
                InRoomEntry(
                    student_id=student.id,
                    student_code=student.student_code,
                    name=student.name,
                    entered_at=entered_at_dt,
                    current_status=status.current_status,
                    cumulative_minutes=cumulative,
                )
            )

        events = [
            AttendanceEventResponse(
                id=e.id,
                student_id=e.student_id,
                student_code=student.student_code,
                student_name=student.name,
                event_type=e.event_type,
                occurred_at=from_unix_seconds(e.occurred_at),
                source=e.source,
            )
            for e, student in self.att_repo.list_today_events(now.date())
        ]

        unknown_card_alert = self.get_latest_unknown_card_alert(now=now)

        return TodayAttendanceResponse(
            in_room=in_room,
            events=events,
            unknown_card_alert=unknown_card_alert,
        )

    def get_latest_unknown_card_alert(self, now: datetime | None = None) -> UnknownCardAlertResponse | None:
        current = ensure_jst(now or now_jst())
        latest_unknown = self.unknown_repo.get_latest()
        if latest_unknown is None:
            return None

        detected_at = from_unix_seconds(latest_unknown.detected_at)
        age_seconds = (current - detected_at).total_seconds()
        if not 0 <= age_seconds <= self.UNKNOWN_CARD_ALERT_WINDOW_SECONDS:
            return None

        return UnknownCardAlertResponse(
            card_id=latest_unknown.card_id,
            reader_name=latest_unknown.reader_name,
            detected_at=detected_at,
        )
