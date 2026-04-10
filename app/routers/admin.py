from fastapi import APIRouter, Depends, Request

from app.admin_session import require_admin_api_auth
from app.deps import get_correction_service
from app.deps import get_attendance_service
from app.kiosk import kiosk_state
from app.schemas.attendance import UnknownCardAlertResponse
from app.schemas.admin import CorrectionRequest
from app.schemas.kiosk import CardCaptureResponse
from app.services.attendance_service import AttendanceService
from app.services.correction_service import CorrectionService

router = APIRouter(prefix="/api/admin", tags=["admin"])
@router.post("/corrections")
def create_correction(
    request: Request,
    payload: CorrectionRequest,
    service: CorrectionService = Depends(get_correction_service),
):
    require_admin_api_auth(request)
    event_id = service.add_correction(payload)
    return {"event_id": event_id}


@router.get("/latest-unknown-card", response_model=UnknownCardAlertResponse | None)
def get_latest_unknown_card(
    request: Request,
    service: AttendanceService = Depends(get_attendance_service),
):
    require_admin_api_auth(request)
    return service.get_latest_unknown_card_alert()


@router.get("/latest-student-card", response_model=CardCaptureResponse | None)
def get_latest_student_card(request: Request):
    require_admin_api_auth(request)
    capture = kiosk_state.get_latest_student_card_capture()
    if capture is None:
        return None
    return CardCaptureResponse(
        card_id=capture.card_id,
        reader_name=capture.reader_name,
        detected_at=capture.detected_at,
    )
