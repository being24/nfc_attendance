from datetime import date

from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TermSettings(Base):
    __tablename__ = "term_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_term: Mapped[int] = mapped_column(Integer, nullable=False)
    first_term_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    second_term_start_date: Mapped[date] = mapped_column(Date, nullable=False)
