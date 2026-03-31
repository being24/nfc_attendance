import pytest

from app.domain.enums import AttendanceAction, AttendanceStatus
from app.domain.state_machine import InvalidTransitionError, get_allowed_actions, next_state


def test_valid_transitions():
    assert next_state(AttendanceStatus.OUTSIDE, AttendanceAction.ENTER) == AttendanceStatus.IN_ROOM
    assert next_state(AttendanceStatus.IN_ROOM, AttendanceAction.LEAVE_TEMP) == AttendanceStatus.OUT_ON_BREAK
    assert next_state(AttendanceStatus.OUT_ON_BREAK, AttendanceAction.RETURN) == AttendanceStatus.IN_ROOM
    assert next_state(AttendanceStatus.IN_ROOM, AttendanceAction.LEAVE_FINAL) == AttendanceStatus.OUTSIDE


def test_invalid_transition():
    with pytest.raises(InvalidTransitionError):
        next_state(AttendanceStatus.OUTSIDE, AttendanceAction.RETURN)


def test_get_allowed_actions():
    assert get_allowed_actions(AttendanceStatus.OUTSIDE) == [AttendanceAction.ENTER]
