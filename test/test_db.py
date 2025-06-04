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
    user_id = db.add_user(card_id, name, is_admin=True)
    user = db.get_user(card_id)
    assert user is not None
    assert user.card_id == card_id
    assert user.name == name
    assert user.id == user_id
    assert user.is_admin is True
    assert hasattr(user, "model_dump")  # pydanticモデルであること


def test_delete_user(temp_db):
    db, _ = temp_db
    card_id = "user_card_002"
    name = "削除ユーザー"
    db.add_user(card_id, name, is_admin=False)
    assert db.delete_user(card_id) is True
    user = db.get_user(card_id)
    assert user is None
    # 存在しないカードIDの削除はFalse
    assert db.delete_user("not_exist_card") is False


def test_list_users(temp_db):
    db, _ = temp_db
    users = [
        ("cardid1", "ユーザー1", True),
        ("cardid2", "ユーザー2", False),
        ("cardid3", "ユーザー3", False),
    ]
    for card_id, name, is_admin in users:
        db.add_user(card_id, name, is_admin=is_admin)
    user_list = db.list_users()
    assert len(user_list) == 3
    card_ids = [u.card_id for u in user_list]
    names = [u.name for u in user_list]
    for card_id, name, is_admin in users:
        assert card_id in card_ids
        assert name in names
        # is_adminの値も一致することを確認
        matched = [u for u in user_list if u.card_id == card_id]
        assert matched and matched[0].is_admin == is_admin
    assert all(hasattr(u, "model_dump") for u in user_list)  # pydanticモデルであること


def test_upsert_user(temp_db):
    db, _ = temp_db
    card_id = "upsert_card_001"
    name1 = "最初の名前"
    name2 = "更新後の名前"
    # 新規追加
    user_id1 = db.upsert_user(card_id, name1, is_admin=False)
    user1 = db.get_user(card_id)
    assert user1 is not None
    assert user1.card_id == card_id
    assert user1.name == name1
    assert user1.is_admin is False
    # 更新
    user_id2 = db.upsert_user(card_id, name2, is_admin=True)
    user2 = db.get_user(card_id)
    assert user2 is not None
    assert user2.card_id == card_id
    assert user2.name == name2
    assert user2.is_admin is True
    # idは同じ
    assert user_id1 == user_id2
