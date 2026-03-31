from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        actor_type: str,
        action: str,
        target_type: str,
        actor_name: str | None = None,
        target_id: int | None = None,
        detail_json: str | None = None,
    ) -> AuditLog:
        rec = AuditLog(
            actor_type=actor_type,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_json=detail_json,
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def list(self) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).order_by(AuditLog.id)).all())
