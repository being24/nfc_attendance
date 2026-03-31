from sqlalchemy.orm import Session

from app.repositories.attendance_repository import AttendanceRepository
from app.schemas.admin import CorrectionRequest
from app.services.audit_service import AuditService


class CorrectionService:
    def __init__(self, db: Session):
        self.att_repo = AttendanceRepository(db)
        self.audit_service = AuditService(db)

    def add_correction(self, payload: CorrectionRequest) -> int:
        event = self.att_repo.add_event(
            student_id=payload.student_id,
            event_type=payload.action.value,
            occurred_at=payload.occurred_at,
            source="admin_correction",
            reader_name=payload.reader_name,
            operator_name=payload.operator_name,
            memo=payload.memo,
        )
        self.audit_service.log(
            actor_type="admin",
            actor_name=payload.operator_name,
            action="ADD_CORRECTION",
            target_type="attendance_event",
            target_id=event.id,
            detail={"student_id": payload.student_id, "action": payload.action.value},
        )
        return event.id
