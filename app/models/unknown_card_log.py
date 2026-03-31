from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.time_utils import now_ts


class UnknownCardLog(Base):
    __tablename__ = "unknown_card_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reader_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ts, nullable=False)
