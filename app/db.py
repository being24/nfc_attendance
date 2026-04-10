from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import get_settings

settings = get_settings()

Base = declarative_base()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if "students" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("students")}
    if "is_admin" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE students ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
