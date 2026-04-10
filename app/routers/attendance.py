import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.deps import get_attendance_service
from app.realtime import attendance_event_broker
from app.schemas.attendance import TodayAttendanceResponse
from app.schemas.touch_panel import TouchPanelActionResponse, TouchPanelActionUpdateRequest
from app.services.attendance_service import AttendanceService
from app.touch_panel import touch_panel_state

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/today", response_model=TodayAttendanceResponse)
def get_today(service: AttendanceService = Depends(get_attendance_service)):
    return service.get_today_attendance()


@router.get("/touch-panel/action", response_model=TouchPanelActionResponse)
def get_touch_panel_action():
    return TouchPanelActionResponse(selected_action=touch_panel_state.get_selected_action())


@router.post("/touch-panel/action", response_model=TouchPanelActionResponse)
def set_touch_panel_action(payload: TouchPanelActionUpdateRequest):
    action = touch_panel_state.set_selected_action(payload.action)
    attendance_event_broker.publish()
    return TouchPanelActionResponse(selected_action=action)


@router.get("/stream")
async def stream_today_events():
    async def event_stream():
        yield "retry: 1000\n"
        yield "data: refresh\n\n"
        async with attendance_event_broker.subscribe() as queue:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {event}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
