from enum import Enum


class AttendanceStatus(str, Enum):
    OUTSIDE = "OUTSIDE"
    IN_ROOM = "IN_ROOM"
    OUT_ON_BREAK = "OUT_ON_BREAK"


class AttendanceAction(str, Enum):
    ENTER = "ENTER"
    LEAVE_TEMP = "LEAVE_TEMP"
    RETURN = "RETURN"
    LEAVE_FINAL = "LEAVE_FINAL"
