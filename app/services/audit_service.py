import json
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(
        self,
        actor_type: str,
        action: str,
        target_type: str,
        actor_name: str | None = None,
        target_id: int | None = None,
        detail: dict | None = None,
    ) -> AuditLog:
        return self.repo.create(
            actor_type=actor_type,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_json=json.dumps(detail, ensure_ascii=False) if detail else None,
        )
