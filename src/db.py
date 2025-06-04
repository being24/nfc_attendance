import csv
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class AttendanceType(IntEnum):
    CLOCK_IN = 1  # 出勤
    CLOCK_OUT = 2  # 退勤
    # 必要に応じて拡張


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    card_id = Column(String, nullable=False)
    type = Column(Integer, nullable=False)  # 出退勤種別はintで保存


class CardUser(Base):
    __tablename__ = "card_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)


class AttendanceDB:
    def __init__(self, db_file=None):
        if db_file is None:
            # プロジェクトルート直下のdataディレクトリを基準にする
            db_dir = Path(__file__).resolve().parents[1] / "data"
            db_dir.mkdir(exist_ok=True)
            db_file = db_dir / "attendance.db"
        self.db_file = db_file
        self.DB_PATH = f"sqlite:///{self.db_file}"
        self.engine = create_engine(self.DB_PATH, echo=False, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

    def add_record(
        self, card_id: str, type_: AttendanceType, timestamp: Optional[datetime] = None
    ):
        if timestamp is None:
            timestamp = datetime.now()
        with self.SessionLocal() as session:
            record = Attendance(timestamp=timestamp, card_id=card_id, type=type_)
            session.add(record)
            session.commit()
            return record.id

    def delete_record(self, record_id: int):
        with self.SessionLocal() as session:
            record = session.get(Attendance, record_id)
            if record:
                session.delete(record)
                session.commit()
                return True
            return False

    def search_records(
        self,
        card_id: Optional[str] = None,
        type_: Optional[AttendanceType] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> list["AttendanceSchema"]:
        with self.SessionLocal() as session:
            query = session.query(Attendance)
            if card_id:
                query = query.filter(Attendance.card_id == card_id)
            if type_ is not None:
                query = query.filter(Attendance.type == type_)
            if year:
                from_dt = datetime(year, month or 1, 1)
                if month:
                    if month == 12:
                        to_dt = datetime(year + 1, 1, 1)
                    else:
                        to_dt = datetime(year, month + 1, 1)
                else:
                    to_dt = datetime(year + 1, 1, 1)
                query = query.filter(
                    Attendance.timestamp >= from_dt, Attendance.timestamp < to_dt
                )
            return [
                AttendanceSchema.model_validate(r)
                for r in query.order_by(Attendance.timestamp).all()
            ]

    def export_csv(self, year: int, month: int, file_path: str):
        records = self.search_records(year=year, month=month)
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "card_id", "type"])
            for r in records:
                writer.writerow([r.id, r.timestamp, r.card_id, r.type])
        return file_path

    def add_user(self, card_id: str, name: str):
        with self.SessionLocal() as session:
            user = CardUser(card_id=card_id, name=name)
            session.add(user)
            session.commit()
            return user.id

    def get_user(self, card_id: str) -> Optional["CardUserSchema"]:
        with self.SessionLocal() as session:
            user = session.query(CardUser).filter_by(card_id=card_id).first()
            return CardUserSchema.model_validate(user) if user else None

    def delete_user(self, card_id: str):
        with self.SessionLocal() as session:
            user = session.query(CardUser).filter_by(card_id=card_id).first()
            if user:
                session.delete(user)
                session.commit()
                return True
            return False

    def list_users(self) -> list["CardUserSchema"]:
        with self.SessionLocal() as session:
            return [
                CardUserSchema.model_validate(u)
                for u in session.query(CardUser).order_by(CardUser.id).all()
            ]


class AttendanceSchema(BaseModel):
    id: int
    timestamp: datetime
    card_id: str
    type: int
    model_config = ConfigDict(from_attributes=True)


class CardUserSchema(BaseModel):
    id: int
    card_id: str
    name: str
    model_config = ConfigDict(from_attributes=True)
