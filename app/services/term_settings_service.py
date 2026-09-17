from datetime import date, datetime

from sqlalchemy.orm import Session

from app.domain.time_utils import ensure_jst, now_jst
from app.models.term_settings import TermSettings
from app.repositories.term_settings_repository import TermSettingsRepository


class TermSettingsService:
    def __init__(self, db: Session):
        self.repo = TermSettingsRepository(db)

    def get_settings(self, now: datetime | None = None) -> TermSettings:
        settings = self.repo.get()
        if settings is not None:
            return settings

        current = ensure_jst(now or now_jst())
        academic_year = current.year if current.month >= 4 else current.year - 1
        active_term = 1 if 4 <= current.month <= 9 else 2
        return self.repo.create(
            active_term=active_term,
            first_term_start_date=date(academic_year, 4, 1),
            second_term_start_date=date(academic_year, 10, 1),
        )

    def update_settings(
        self,
        active_term: int,
        first_term_start_date: date,
        second_term_start_date: date,
    ) -> TermSettings:
        if active_term not in {1, 2}:
            raise ValueError("学期は前期または後期を指定してください")
        if first_term_start_date >= second_term_start_date:
            raise ValueError("前期開始日は後期開始日より前の日付にしてください")

        settings = self.get_settings()
        return self.repo.update(
            settings,
            active_term,
            first_term_start_date,
            second_term_start_date,
        )
