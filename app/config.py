import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./attendance.db")
    reader_token: str = os.getenv("READER_TOKEN", "dev-reader-token")
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "dev-session-secret")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin")
    admin_card_ids: str = os.getenv("ADMIN_CARD_IDS", "ADMIN-CARD-001")


def get_settings() -> Settings:
    return Settings()
