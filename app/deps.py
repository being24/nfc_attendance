from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.attendance_service import AttendanceService
from app.services.correction_service import CorrectionService
from app.services.student_service import StudentService


def get_student_service(db: Session = Depends(get_db)) -> StudentService:
    return StudentService(db)


def get_attendance_service(db: Session = Depends(get_db)) -> AttendanceService:
    return AttendanceService(db)


def get_correction_service(db: Session = Depends(get_db)) -> CorrectionService:
    return CorrectionService(db)
