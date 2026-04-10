from argparse import Namespace

import httpx

from reader import main as reader_main


def silence_reader_logger(monkeypatch):
    monkeypatch.setattr(reader_main.logger, "exception", lambda *args, **kwargs: None)
    monkeypatch.setattr(reader_main.logger, "error", lambda *args, **kwargs: None)


def make_args(**overrides):
    base = {
        "base_url": "http://localhost:8000",
        "reader_token": "token",
        "reader_name": None,
        "card_id": None,
        "action": "auto",
        "cooldown": 2.0,
        "interval": 0.1,
        "count": 1,
        "loop": False,
        "device_keyword": "SONY FeliCa",
    }
    base.update(overrides)
    return Namespace(**base)


def test_main_uses_dummy_mode_when_card_id_is_present(monkeypatch):
    monkeypatch.setattr(reader_main, "parse_args", lambda: make_args(card_id="CARD1"))
    monkeypatch.setattr(reader_main, "ReaderApiClient", lambda **kwargs: object())
    monkeypatch.setattr(reader_main, "Debouncer", lambda cooldown_seconds: object())
    calls = []
    monkeypatch.setattr(reader_main, "run_dummy_mode", lambda args, client, debouncer: calls.append(args.card_id) or 0)
    monkeypatch.setattr(reader_main, "run_real_mode", lambda args, client, debouncer: 1)

    result = reader_main.main()

    assert result == 0
    assert calls == ["CARD1"]


def test_main_uses_real_mode_when_card_id_is_missing(monkeypatch):
    monkeypatch.setattr(reader_main, "parse_args", lambda: make_args(card_id=None))
    monkeypatch.setattr(reader_main, "ReaderApiClient", lambda **kwargs: object())
    monkeypatch.setattr(reader_main, "Debouncer", lambda cooldown_seconds: object())
    calls = []
    monkeypatch.setattr(reader_main, "run_dummy_mode", lambda args, client, debouncer: 1)
    monkeypatch.setattr(reader_main, "run_real_mode", lambda args, client, debouncer: calls.append(args.device_keyword) or 0)

    result = reader_main.main()

    assert result == 0
    assert calls == ["SONY FeliCa"]


def test_resolve_reader_name_defaults_by_mode():
    assert reader_main.resolve_reader_name(make_args(card_id="CARD1")) == "dummy-reader"
    assert reader_main.resolve_reader_name(make_args(card_id=None)) == "real-reader"


def test_resolve_reader_name_prefers_explicit_value():
    assert reader_main.resolve_reader_name(make_args(card_id=None, reader_name="reader-a")) == "reader-a"


def test_build_card_event_handler_processes_insert(monkeypatch):
    silence_reader_logger(monkeypatch)
    calls = []

    def fake_run_once(client, debouncer, card_id, reader_name, action):
        calls.append((card_id, reader_name, action))

    monkeypatch.setattr(reader_main, "run_once", fake_run_once)
    handler = reader_main.build_card_event_handler(object(), object(), "reader-a", "auto")

    handler("insert", "CARD1")
    handler("remove", None)

    assert calls == [("CARD1", "reader-a", "auto")]


def test_build_card_event_handler_swallows_processing_errors(monkeypatch):
    silence_reader_logger(monkeypatch)
    def fake_run_once(client, debouncer, card_id, reader_name, action):
        raise RuntimeError("boom")

    monkeypatch.setattr(reader_main, "run_once", fake_run_once)
    handler = reader_main.build_card_event_handler(object(), object(), "reader-a", "auto")

    handler("insert", "CARD1")


def test_build_card_event_handler_ignores_reader_errors(monkeypatch):
    silence_reader_logger(monkeypatch)
    calls = []
    monkeypatch.setattr(reader_main, "run_once", lambda *args, **kwargs: calls.append("called"))
    handler = reader_main.build_card_event_handler(object(), object(), "reader-a", "auto")

    handler("insert", None, RuntimeError("boom"))

    assert calls == []


def test_summarize_http_error_uses_response_detail():
    request = httpx.Request("POST", "http://localhost:8000/api/reader/touches")
    response = httpx.Response(404, json={"detail": "未登録のカードです"}, request=request)
    exc = httpx.HTTPStatusError("not found", request=request, response=response)

    summary = reader_main.summarize_http_error(exc)

    assert summary == "status=404 detail=未登録のカードです"


def test_build_card_event_handler_swallows_http_errors(monkeypatch):
    silence_reader_logger(monkeypatch)

    def fake_run_once(client, debouncer, card_id, reader_name, action):
        request = httpx.Request("POST", "http://localhost:8000/api/reader/touches")
        response = httpx.Response(404, json={"detail": "未登録のカードです"}, request=request)
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr(reader_main, "run_once", fake_run_once)
    handler = reader_main.build_card_event_handler(object(), object(), "reader-a", "auto")

    handler("insert", "CARD1")
