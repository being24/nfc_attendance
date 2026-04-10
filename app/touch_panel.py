from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock

from app.domain.enums import AttendanceAction
from app.domain.time_utils import ensure_jst, now_jst


class TouchPanelSelection(str, Enum):
    ENTER = AttendanceAction.ENTER.value
    LEAVE_TEMP = AttendanceAction.LEAVE_TEMP.value
    RETURN = AttendanceAction.RETURN.value
    LEAVE_FINAL = AttendanceAction.LEAVE_FINAL.value
    TERM_TOTAL = "TERM_TOTAL"


@dataclass
class TermTotalDisplay:
    student_code: str
    student_name: str
    total_minutes: int
    period_label: str
    detected_at: datetime


@dataclass
class TouchPanelErrorDisplay:
    message: str
    detected_at: datetime


class TouchPanelState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._selected_action = TouchPanelSelection.ENTER
        self._latest_term_total: TermTotalDisplay | None = None
        self._latest_error: TouchPanelErrorDisplay | None = None

    def get_selected_action(self) -> TouchPanelSelection:
        with self._lock:
            return self._selected_action

    def set_selected_action(self, action: TouchPanelSelection) -> TouchPanelSelection:
        with self._lock:
            self._selected_action = action
            return self._selected_action

    def get_selected_attendance_action(self) -> AttendanceAction | None:
        with self._lock:
            if self._selected_action == TouchPanelSelection.TERM_TOTAL:
                return None
            return AttendanceAction(self._selected_action.value)

    def store_term_total_display(
        self,
        student_code: str,
        student_name: str,
        total_minutes: int,
        period_label: str,
        detected_at: datetime,
    ) -> TermTotalDisplay:
        with self._lock:
            self._latest_term_total = TermTotalDisplay(
                student_code=student_code,
                student_name=student_name,
                total_minutes=total_minutes,
                period_label=period_label,
                detected_at=ensure_jst(detected_at),
            )
            return self._latest_term_total

    def store_error(self, message: str, detected_at: datetime) -> TouchPanelErrorDisplay:
        with self._lock:
            self._latest_error = TouchPanelErrorDisplay(message=message, detected_at=ensure_jst(detected_at))
            return self._latest_error

    def get_latest_error(self, now: datetime | None = None, ttl_seconds: int = 30) -> TouchPanelErrorDisplay | None:
        with self._lock:
            latest = self._latest_error
        if latest is None:
            return None
        current = ensure_jst(now or now_jst())
        if current - latest.detected_at > timedelta(seconds=ttl_seconds):
            return None
        return latest

    def get_latest_term_total_display(self, now: datetime | None = None, ttl_seconds: int = 30) -> TermTotalDisplay | None:
        with self._lock:
            latest = self._latest_term_total
        if latest is None:
            return None
        current = ensure_jst(now or now_jst())
        if current - latest.detected_at > timedelta(seconds=ttl_seconds):
            return None
        return latest


touch_panel_state = TouchPanelState()
