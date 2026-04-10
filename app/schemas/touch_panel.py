from pydantic import BaseModel

from app.domain.enums import AttendanceAction


class TouchPanelActionResponse(BaseModel):
    selected_action: AttendanceAction


class TouchPanelActionUpdateRequest(BaseModel):
    action: AttendanceAction
