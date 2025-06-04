import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.db import AttendanceDB, AttendanceType

import time
from datetime import datetime
from typing import Optional

from smartcard.System import readers as get_readers
from smartcard.util import toHexString


class NFCReaderError(Exception):
    pass


class NFCReader:
    def __init__(self, reader_name_keyword: str = "SONY FeliCa"):
        self.reader_name_keyword = reader_name_keyword
        self.reader_index: Optional[int] = None
        self.readers = get_readers()
        self._select_reader()

    def _select_reader(self):
        for i, reader in enumerate(self.readers):
            if self.reader_name_keyword in reader.name:
                self.reader_index = i
                return
        raise NFCReaderError(
            f"No reader found with keyword: {self.reader_name_keyword}"
        )

    def read_card_id(self) -> str:
        if self.reader_index is None:
            raise NFCReaderError("No NFC reader selected.")
        try:
            conn = self.readers[self.reader_index].createConnection()
            conn.connect()
            send_data = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            recv_data, sw1, sw2 = conn.transmit(send_data)
            card_id = toHexString(recv_data).replace(" ", "")
            return card_id
        except Exception as e:
            raise NFCReaderError(f"Failed to read card: {e}")


def select_attendance_type() -> AttendanceType:
    while True:
        t = input("Type (1:出勤, 2:退勤): ")
        if t in ("1", "2"):
            return AttendanceType(int(t))
        print("1か2を入力してください")


def main():
    db = AttendanceDB()
    try:
        nfc = NFCReader()
    except NFCReaderError as e:
        print(e)
        return
    print("Please touch your card...")
    while True:
        try:
            card_id = nfc.read_card_id()
            print(f"Card ID: {card_id}")
            type_ = select_attendance_type()
            db.add_record(card_id, type_, datetime.now())
            print("記録しました。")
            break
        except NFCReaderError as e:
            print(f"カード待機中... {e}")
            time.sleep(1)
        except Exception as e:
            print(f"予期せぬエラー: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
