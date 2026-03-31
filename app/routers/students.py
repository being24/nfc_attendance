from fastapi import APIRouter, Depends

from app.deps import get_student_service
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=list[StudentResponse])
def list_students(service: StudentService = Depends(get_student_service)):
    return service.list_students(include_inactive=False)


@router.post("", response_model=StudentResponse, status_code=201)
def create_student(payload: StudentCreate, service: StudentService = Depends(get_student_service)):
    return service.register_student(payload)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, service: StudentService = Depends(get_student_service)):
    return service.get_student(student_id)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    service: StudentService = Depends(get_student_service),
):
    return service.update_student(student_id, payload)
