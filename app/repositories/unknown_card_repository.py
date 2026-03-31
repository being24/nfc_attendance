from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.time_utils import to_unix_seconds
from app.models.unknown_card_log import UnknownCardLog


class UnknownCardRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, card_id: str, reader_name: str | None, detected_at: datetime) -> UnknownCardLog:
        rec = UnknownCardLog(
            card_id=card_id,
            reader_name=reader_name,
            detected_at=to_unix_seconds(detected_at),
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def list(self) -> list[UnknownCardLog]:
        return list(self.db.scalars(select(UnknownCardLog).order_by(UnknownCardLog.id)).all())
