from __future__ import annotations

from threading import Lock

from app.domain.enums import AttendanceAction


class TouchPanelState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._selected_action = AttendanceAction.ENTER

    def get_selected_action(self) -> AttendanceAction:
        with self._lock:
            return self._selected_action

    def set_selected_action(self, action: AttendanceAction) -> AttendanceAction:
        with self._lock:
            self._selected_action = action
            return self._selected_action


touch_panel_state = TouchPanelState()
