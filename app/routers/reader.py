from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_settings
from app.deps import get_attendance_service
from app.schemas.reader import (
    ReaderTouchConfirmRequest,
    ReaderTouchConfirmResponse,
    ReaderTouchRequest,
    ReaderTouchResponse,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/reader", tags=["reader"])
settings = get_settings()


def require_reader_token(x_reader_token: str = Header(alias="X-Reader-Token")) -> None:
    if x_reader_token != settings.reader_token:
        raise HTTPException(status_code=401, detail="invalid reader token")


@router.post("/touches", response_model=ReaderTouchResponse, dependencies=[Depends(require_reader_token)])
def create_touch(
    payload: ReaderTouchRequest,
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.prepare_touch(payload.card_id, payload.reader_name, payload.detected_at)


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
