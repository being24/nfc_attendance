from fastapi import APIRouter, Depends

from app.deps import get_attendance_service
from app.schemas.attendance import TodayAttendanceResponse
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/today", response_model=TodayAttendanceResponse)
def get_today(service: AttendanceService = Depends(get_attendance_service)):
    return service.get_today_attendance()
