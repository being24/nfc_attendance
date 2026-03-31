from app.repositories.audit_repository import AuditRepository


def test_audit_repository(db_session):
    repo = AuditRepository(db_session)
    repo.create(actor_type="admin", action="EDIT", target_type="student", target_id=1)
    rows = repo.list()
    assert len(rows) == 1
    assert rows[0].action == "EDIT"
