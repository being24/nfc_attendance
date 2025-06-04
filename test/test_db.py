import shutil
import sys
from datetime import datetime
from pathlib import Path
import tempfile

import pytest

# プロジェクトroot（srcの親）をsys.pathに追加（parents[1]でrootを取得）
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.db import AttendanceDB, AttendanceType


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
    assert all(hasattr(r, "model_dump") for r in results)  # pydanticモデルであること


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


def test_add_and_get_user(temp_db):
    db, _ = temp_db
    card_id = "user_card_001"
    name = "テスト太郎"
    user_id = db.add_user(card_id, name)
    user = db.get_user(card_id)
    assert user is not None
    assert user.card_id == card_id
    assert user.name == name
    assert user.id == user_id
    assert hasattr(user, "model_dump")  # pydanticモデルであること


def test_delete_user(temp_db):
    db, _ = temp_db
    card_id = "user_card_002"
    name = "削除ユーザー"
    db.add_user(card_id, name)
    assert db.delete_user(card_id) is True
    user = db.get_user(card_id)
    assert user is None
    # 存在しないカードIDの削除はFalse
    assert db.delete_user("not_exist_card") is False


def test_list_users(temp_db):
    db, _ = temp_db
    users = [
        ("cardid1", "ユーザー1"),
        ("cardid2", "ユーザー2"),
        ("cardid3", "ユーザー3"),
    ]
    for card_id, name in users:
        db.add_user(card_id, name)
    user_list = db.list_users()
    assert len(user_list) == 3
    card_ids = [u.card_id for u in user_list]
    names = [u.name for u in user_list]
    for card_id, name in users:
        assert card_id in card_ids
        assert name in names
    assert all(hasattr(u, "model_dump") for u in user_list)  # pydanticモデルであること
