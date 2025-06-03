import os
import shutil

# srcディレクトリをimportパスに追加
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from db import AttendanceDB, AttendanceType


@pytest.fixture
def temp_db():
    test_data_dir = Path(tempfile.mkdtemp())
    db_file = test_data_dir / "attendance_test.db"
    db = AttendanceDB(db_file=db_file)
    print(f"[TEST] test_data_dir: {test_data_dir}")
    yield db, test_data_dir
    db.engine.dispose()  # DB接続を明示的に閉じる
    shutil.rmtree(test_data_dir)  # 一時ディレクトリ削除を一時的に無効化


def test_add_and_search_record(temp_db):
    db, _ = temp_db
    card_id = "test_card"
    type_ = AttendanceType.CLOCK_IN
    now = datetime.now()
    record_id = db.add_record(card_id, type_, now)
    results = db.search_records(card_id=card_id)
    assert any(r.id == record_id for r in results)
    assert any(r.card_id == card_id for r in results)
    assert any(r.type == type_ for r in results)


def test_delete_record(temp_db):
    db, _ = temp_db
    card_id = "delete_card"
    type_ = AttendanceType.CLOCK_OUT
    now = datetime.now()
    record_id = db.add_record(card_id, type_, now)
    assert db.delete_record(record_id) is True
    results = db.search_records(card_id=card_id)
    assert all(r.id != record_id for r in results)


def test_export_csv(temp_db):
    db, test_data_dir = temp_db
    card_id = "csv_card"
    type_ = AttendanceType.CLOCK_IN
    now = datetime(2025, 6, 3)
    db.add_record(card_id, type_, now)
    csv_path = test_data_dir / "test.csv"
    db.export_csv(2025, 6, str(csv_path))
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()
    assert any("csv_card" in line for line in lines)
    csv_path.unlink()
