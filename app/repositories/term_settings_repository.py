from datetime import date

from sqlalchemy.orm import Session

from app.models.term_settings import TermSettings


class TermSettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> TermSettings | None:
        return self.db.get(TermSettings, 1)

    def create(
        self,
        active_term: int,
        first_term_start_date: date,
        second_term_start_date: date,
    ) -> TermSettings:
        settings = TermSettings(
            id=1,
            active_term=active_term,
            first_term_start_date=first_term_start_date,
            second_term_start_date=second_term_start_date,
        )
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def update(
        self,
        settings: TermSettings,
        active_term: int,
        first_term_start_date: date,
        second_term_start_date: date,
    ) -> TermSettings:
        settings.active_term = active_term
        settings.first_term_start_date = first_term_start_date
        settings.second_term_start_date = second_term_start_date
        self.db.commit()
        self.db.refresh(settings)
        return settings
