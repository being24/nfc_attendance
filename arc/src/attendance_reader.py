import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.db import AttendanceDB, AttendanceType

import time
from datetime import datetime
from typing import Optional

from smartcard.System import readers as get_readers
from smartcard.util import toHexString
from smartcard.CardMonitoring import CardMonitor, CardObserver


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


class CardEventObserver(CardObserver):
    """
    カードの挿入（タッチ）・離脱イベントを検知し、
    callback(event_type, card_id, error=None) を呼び出す。
    event_type: 'insert' or 'remove'
    card_id: カードID（remove時はNoneになる場合あり）
    """

    def __init__(self, callback):
        self.callback = callback

    def update(self, observable, handlers):
        added_cards, removed_cards = handlers
        for card in added_cards:
            try:
                connection = card.createConnection()
                connection.connect()
                send_data = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                data, sw1, sw2 = connection.transmit(send_data)
                card_id = toHexString(data).replace(" ", "")
                self.callback("insert", card_id)
            except Exception as e:
                self.callback("insert", None, error=e)
        for card in removed_cards:
            # 離脱時はカードIDが取得できない場合が多いのでNoneで通知
            self.callback("remove", None)


def select_attendance_type() -> AttendanceType:
    while True:
        t = input("Type (1:出勤, 2:退勤): ")
        if t in ("1", "2"):
            return AttendanceType(int(t))
        print("1か2を入力してください")


def main():
    monitor = CardMonitor()
    print("Please touch your card...")

    def on_card(event_type, card_id, error=None):
        print(f"event_type={event_type}, card_id={card_id}")
        if error:
            print(f"Error: {error}")
        # ここではdeleteObserverやsys.exitは呼ばず、イベント表示のみ

    observer = CardEventObserver(on_card)
    monitor.addObserver(observer)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("終了します。")
        monitor.deleteObserver(observer)


if __name__ == "__main__":
    main()
