from app.domain.enums import AttendanceAction, AttendanceStatus


class InvalidTransitionError(ValueError):
    pass


TRANSITIONS: dict[AttendanceStatus, dict[AttendanceAction, AttendanceStatus]] = {
    AttendanceStatus.OUTSIDE: {
        AttendanceAction.ENTER: AttendanceStatus.IN_ROOM,
    },
    AttendanceStatus.IN_ROOM: {
        AttendanceAction.LEAVE_TEMP: AttendanceStatus.OUT_ON_BREAK,
        AttendanceAction.LEAVE_FINAL: AttendanceStatus.OUTSIDE,
    },
    AttendanceStatus.OUT_ON_BREAK: {
        AttendanceAction.RETURN: AttendanceStatus.IN_ROOM,
    },
}


def get_allowed_actions(state: AttendanceStatus) -> list[AttendanceAction]:
    return list(TRANSITIONS.get(state, {}).keys())


def next_state(state: AttendanceStatus, action: AttendanceAction) -> AttendanceStatus:
    state_transitions = TRANSITIONS.get(state, {})
    if action not in state_transitions:
        raise InvalidTransitionError(f"Invalid transition: {state} + {action}")
    return state_transitions[action]
