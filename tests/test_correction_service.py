from app.domain.enums import AttendanceAction
from app.domain.time_utils import now_jst
from app.repositories.audit_repository import AuditRepository
from app.schemas.admin import CorrectionRequest
from app.schemas.student import StudentCreate
from app.services.correction_service import CorrectionService
from app.services.student_service import StudentService


def test_correction_creates_event_and_audit(db_session):
    student = StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = CorrectionService(db_session)
    event_id = svc.add_correction(
        CorrectionRequest(
            student_id=student.id,
            action=AttendanceAction.ENTER,
            occurred_at=now_jst(),
            operator_name="admin",
            memo="manual",
        )
    )
    assert event_id > 0
    logs = AuditRepository(db_session).list()
    assert len(logs) == 1
    assert logs[0].action == "ADD_CORRECTION"
