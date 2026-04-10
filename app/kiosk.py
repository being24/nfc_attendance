from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import Lock

from app.domain.time_utils import ensure_jst, now_jst


class KioskMode(str, Enum):
    ATTENDANCE = "ATTENDANCE"
    ADMIN_LOGIN = "ADMIN_LOGIN"
    STUDENT_REGISTER = "STUDENT_REGISTER"


@dataclass
class CardCapture:
    card_id: str
    reader_name: str | None
    detected_at: datetime


class KioskState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._mode = KioskMode.ATTENDANCE
        self._latest_admin_login_capture: CardCapture | None = None
        self._latest_student_card_capture: CardCapture | None = None

    def get_mode(self) -> KioskMode:
        with self._lock:
            return self._mode

    def set_mode(self, mode: KioskMode) -> KioskMode:
        with self._lock:
            self._mode = mode
            return self._mode

    def store_admin_login_capture(self, card_id: str, reader_name: str | None, detected_at: datetime) -> None:
        with self._lock:
            self._latest_admin_login_capture = CardCapture(card_id, reader_name, ensure_jst(detected_at))

    def clear_admin_login_capture(self) -> None:
        with self._lock:
            self._latest_admin_login_capture = None

    def store_student_card_capture(self, card_id: str, reader_name: str | None, detected_at: datetime) -> None:
        with self._lock:
            self._latest_student_card_capture = CardCapture(card_id, reader_name, ensure_jst(detected_at))

    def get_latest_admin_login_capture(self, now: datetime | None = None, ttl_seconds: int = 30) -> CardCapture | None:
        current = ensure_jst(now or now_jst())
        with self._lock:
            capture = self._latest_admin_login_capture
        if capture is None or (current - capture.detected_at).total_seconds() > ttl_seconds:
            return None
        return capture

    def get_latest_student_card_capture(self, now: datetime | None = None, ttl_seconds: int = 30) -> CardCapture | None:
        current = ensure_jst(now or now_jst())
        with self._lock:
            capture = self._latest_student_card_capture
        if capture is None or (current - capture.detected_at).total_seconds() > ttl_seconds:
            return None
        return capture


kiosk_state = KioskState()
