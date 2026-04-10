from __future__ import annotations

from typing import Callable

try:
    from smartcard.CardMonitoring import CardMonitor, CardObserver as SmartcardCardObserver
    from smartcard.System import readers as get_readers
    from smartcard.util import toHexString
except ImportError as exc:  # pragma: no cover - exercised via tests with monkeypatch
    CardMonitor = None

    class SmartcardCardObserver:  # type: ignore[no-redef]
        pass

    def get_readers():
        return []

    def toHexString(data: list[int]) -> str:
        return " ".join(f"{value:02X}" for value in data)

    SMARTCARD_IMPORT_ERROR: Exception | None = exc
else:
    SMARTCARD_IMPORT_ERROR = None


UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]


class NFCReaderError(Exception):
    pass


class NFCReaderUnavailableError(NFCReaderError):
    pass


class NFCReaderNotFoundError(NFCReaderError):
    pass


class NFCReadCardError(NFCReaderError):
    pass


def ensure_smartcard_available() -> None:
    if SMARTCARD_IMPORT_ERROR is not None:
        raise NFCReaderUnavailableError("pyscard が利用できません。PC/SC と pyscard を確認してください。") from SMARTCARD_IMPORT_ERROR


class NFCReader:
    def __init__(self, reader_name_keyword: str = "SONY FeliCa"):
        ensure_smartcard_available()
        self.reader_name_keyword = reader_name_keyword
        self.readers = list(get_readers())
        self.reader = self._select_reader()

    def _select_reader(self):
        for reader in self.readers:
            if self.reader_name_keyword in reader.name:
                return reader
        raise NFCReaderNotFoundError(f"No reader found with keyword: {self.reader_name_keyword}")

    @staticmethod
    def read_card_id_from_card(card) -> str:
        try:
            connection = card.createConnection()
            connection.connect()
            data, sw1, sw2 = connection.transmit(UID_APDU)
        except Exception as exc:  # pragma: no cover - driver dependent
            raise NFCReadCardError(f"Failed to read card: {exc}") from exc
        if (sw1, sw2) != (0x90, 0x00):
            raise NFCReadCardError(f"Reader returned unexpected status: {sw1:02X} {sw2:02X}")
        return toHexString(data).replace(" ", "")

    def read_card_id(self) -> str:
        return self.read_card_id_from_card(self.reader)


class CardEventObserver(SmartcardCardObserver):
    def __init__(self, callback: Callable[[str, str | None, Exception | None], None]):
        self.callback = callback

    def update(self, observable, handlers) -> None:
        added_cards, removed_cards = handlers
        for card in added_cards:
            try:
                card_id = NFCReader.read_card_id_from_card(card)
            except Exception as exc:
                self.callback("insert", None, exc)
            else:
                self.callback("insert", card_id, None)
        for _ in removed_cards:
            self.callback("remove", None, None)


class NFCMonitor:
    def __init__(self, reader_name_keyword: str, callback: Callable[[str, str | None, Exception | None], None]):
        ensure_smartcard_available()
        self.reader = NFCReader(reader_name_keyword=reader_name_keyword)
        if CardMonitor is None:
            raise NFCReaderUnavailableError("CardMonitor を初期化できません")
        self.monitor = CardMonitor()
        self.observer = CardEventObserver(callback)
        self.started = False

    def start(self) -> None:
        if self.started:
            return
        self.monitor.addObserver(self.observer)
        self.started = True

    def stop(self) -> None:
        if not self.started:
            return
        self.monitor.deleteObserver(self.observer)
        self.started = False
