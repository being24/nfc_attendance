from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_settings
from app.deps import get_attendance_service
from app.kiosk import kiosk_state
from app.realtime import attendance_event_broker
from app.schemas.kiosk import KioskModeResponse
from app.schemas.touch_panel import TouchPanelErrorCaptureRequest
from app.schemas.reader import (
    ReaderTouchConfirmRequest,
    ReaderTouchConfirmResponse,
    ReaderTouchRequest,
    ReaderTouchResponse,
)
from app.services.attendance_service import AttendanceService
from app.touch_panel import touch_panel_state

router = APIRouter(prefix="/api/reader", tags=["reader"])
settings = get_settings()


def require_reader_token(x_reader_token: str = Header(alias="X-Reader-Token")) -> None:
    if x_reader_token != settings.reader_token:
        raise HTTPException(status_code=401, detail="リーダートークンが無効です")


@router.post("/touches", response_model=ReaderTouchResponse, dependencies=[Depends(require_reader_token)])
def create_touch(
    payload: ReaderTouchRequest,
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.prepare_touch(payload.card_id, payload.reader_name, payload.detected_at)


@router.post("/captures/admin-login", dependencies=[Depends(require_reader_token)])
def capture_admin_login_card(payload: ReaderTouchRequest):
    kiosk_state.store_admin_login_capture(payload.card_id, payload.reader_name, payload.detected_at)
    attendance_event_broker.publish()
    return {"ok": True}


@router.post("/captures/student-card", dependencies=[Depends(require_reader_token)])
def capture_student_card(payload: ReaderTouchRequest):
    kiosk_state.store_student_card_capture(payload.card_id, payload.reader_name, payload.detected_at)
    attendance_event_broker.publish()
    return {"ok": True}


@router.post("/captures/term-total", dependencies=[Depends(require_reader_token)])
def capture_term_total(
    payload: ReaderTouchRequest,
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.capture_current_term_total_by_card(payload.card_id, payload.reader_name, payload.detected_at)


@router.post("/captures/touch-error", dependencies=[Depends(require_reader_token)])
def capture_touch_error(payload: TouchPanelErrorCaptureRequest):
    touch_panel_state.store_error(message=payload.message, detected_at=payload.detected_at)
    attendance_event_broker.publish()
    return {"ok": True}


@router.get("/kiosk-mode", response_model=KioskModeResponse, dependencies=[Depends(require_reader_token)])
def get_kiosk_mode():
    return KioskModeResponse(mode=kiosk_state.get_mode())


@router.post(
    "/touches/{touch_token}/confirm",
    response_model=ReaderTouchConfirmResponse,
    dependencies=[Depends(require_reader_token)],
)
def confirm_touch(
    touch_token: str,
    payload: ReaderTouchConfirmRequest,
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.confirm_touch(touch_token, payload.action, payload.now)
