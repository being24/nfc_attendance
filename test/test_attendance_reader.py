import time
from datetime import datetime
from typing import Optional
import pytest
from src.db import AttendanceDB, AttendanceType
from src.attendance_reader import NFCReader, NFCReaderError, select_attendance_type


def test_nfc_reader_card_id(monkeypatch):
    # NFCリーダーがない環境用のモック
    class DummyReader:
        name = "SONY FeliCa Dummy"

        def createConnection(self):
            class Conn:
                def connect(self):
                    pass

                def transmit(self, send_data):
                    # ダミーのカードIDデータ
                    return [1, 2, 3, 4, 5, 6, 7, 8], 0x90, 0x00

            return Conn()

    monkeypatch.setattr("src.attendance_reader.get_readers", lambda: [DummyReader()])
    nfc = NFCReader()
    card_id = nfc.read_card_id()
    assert card_id == "0102030405060708"


def test_select_attendance_type(monkeypatch):
    # 入力を1にモック
    monkeypatch.setattr("builtins.input", lambda _: "1")
    t = select_attendance_type()
    assert t == AttendanceType.CLOCK_IN
    # 入力を2にモック
    monkeypatch.setattr("builtins.input", lambda _: "2")
    t = select_attendance_type()
    assert t == AttendanceType.CLOCK_OUT


def test_main_flow(monkeypatch):
    # NFCリーダーとinputをモック
    class DummyReader:
        name = "SONY FeliCa Dummy"

        def createConnection(self):
            class Conn:
                def connect(self):
                    pass

                def transmit(self, send_data):
                    return [1, 2, 3, 4, 5, 6, 7, 8], 0x90, 0x00

            return Conn()

    monkeypatch.setattr("src.attendance_reader.get_readers", lambda: [DummyReader()])
    monkeypatch.setattr("builtins.input", lambda _: "1")
    db = AttendanceDB()
    nfc = NFCReader()
    card_id = nfc.read_card_id()
    type_ = select_attendance_type()
    record_id = db.add_record(card_id, type_, datetime.now())
    results = db.search_records(card_id=card_id)
    assert any(r.id == record_id for r in results)
    assert any(r.type == type_ for r in results)
