import pytest

from reader import nfc


class DummyConnection:
    def __init__(self, data=None, sw1=0x90, sw2=0x00, error: Exception | None = None):
        self.data = data or [0x01, 0x02, 0x03, 0x04]
        self.sw1 = sw1
        self.sw2 = sw2
        self.error = error

    def connect(self):
        if self.error is not None:
            raise self.error

    def transmit(self, send_data):
        return self.data, self.sw1, self.sw2


class DummyCard:
    def __init__(self, connection: DummyConnection):
        self.connection = connection

    def createConnection(self):
        return self.connection


class DummyReader:
    def __init__(self, name: str, connection: DummyConnection | None = None):
        self.name = name
        self.connection = connection or DummyConnection()

    def createConnection(self):
        return self.connection


def test_nfc_reader_selects_reader_by_keyword(monkeypatch):
    monkeypatch.setattr(nfc, "SMARTCARD_IMPORT_ERROR", None)
    monkeypatch.setattr(
        nfc,
        "get_readers",
        lambda: [DummyReader("Other Reader"), DummyReader("SONY FeliCa RC-S300")],
    )

    reader = nfc.NFCReader()

    assert reader.reader.name == "SONY FeliCa RC-S300"


def test_nfc_reader_raises_when_reader_not_found(monkeypatch):
    monkeypatch.setattr(nfc, "SMARTCARD_IMPORT_ERROR", None)
    monkeypatch.setattr(nfc, "get_readers", lambda: [DummyReader("Other Reader")])

    with pytest.raises(nfc.NFCReaderNotFoundError):
        nfc.NFCReader()


def test_nfc_reader_reads_card_id(monkeypatch):
    monkeypatch.setattr(nfc, "SMARTCARD_IMPORT_ERROR", None)
    monkeypatch.setattr(nfc, "get_readers", lambda: [DummyReader("SONY FeliCa", DummyConnection(data=[0xAA, 0xBB]))])

    reader = nfc.NFCReader()

    assert reader.read_card_id() == "AABB"


def test_card_event_observer_emits_insert(monkeypatch):
    monkeypatch.setattr(nfc, "SMARTCARD_IMPORT_ERROR", None)
    events = []
    observer = nfc.CardEventObserver(lambda event_type, card_id, error=None: events.append((event_type, card_id, error)))

    observer.update(None, ([DummyCard(DummyConnection(data=[0x10, 0x20]))], []))

    assert events == [("insert", "1020", None)]


def test_card_event_observer_emits_error_on_read_failure(monkeypatch):
    monkeypatch.setattr(nfc, "SMARTCARD_IMPORT_ERROR", None)
    events = []
    observer = nfc.CardEventObserver(lambda event_type, card_id, error=None: events.append((event_type, card_id, error)))

    observer.update(None, ([DummyCard(DummyConnection(error=RuntimeError("boom")))], []))

    assert events[0][0] == "insert"
    assert events[0][1] is None
    assert isinstance(events[0][2], nfc.NFCReadCardError)
