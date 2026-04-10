import os
from dataclasses import dataclass

from app.env import load_project_dotenv


load_project_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./attendance.db")
    reader_token: str = os.getenv("READER_TOKEN", "dev-reader-token")
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "dev-session-secret")
    session_max_age_seconds: int = int(os.getenv("SESSION_MAX_AGE_SECONDS", "300"))
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin")


def get_settings() -> Settings:
    return Settings()
