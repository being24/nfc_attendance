from datetime import datetime

import httpx

from reader.client import ReaderApiClient


def test_reader_client_prepare_and_confirm(monkeypatch):
    routes = {
        "http://localhost:8000/api/attendance/touch-panel/action": {
            "selected_action": "ENTER",
        },
        "http://localhost:8000/api/reader/kiosk-mode": {
            "mode": "ATTENDANCE",
        },
        "http://localhost:8000/api/reader/touches": {
            "touch_token": "tok123",
            "allowed_actions": ["ENTER"],
        },
        "http://localhost:8000/api/reader/captures/term-total": {
            "student_code": "S001",
            "student_name": "Alice",
            "total_minutes": 75,
            "period_label": "2026-04-01 〜 2026-04-10",
            "detected_at": "2026-04-10T00:00:00+09:00",
        },
        "http://localhost:8000/api/reader/captures/touch-error": {
            "ok": True,
        },
        "http://localhost:8000/api/reader/touches/tok123/confirm": {
            "next_status": "IN_ROOM",
            "lock_alert_required": False,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        data = routes.get(str(request.url))
        if data is None:
            return httpx.Response(404, json={"detail": "not found"})
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("reader.client.httpx.Client", PatchedClient)

    client = ReaderApiClient(base_url="http://localhost:8000", reader_token="token")
    selected = client.get_touch_panel_action()
    assert selected["selected_action"] == "ENTER"

    mode = client.get_kiosk_mode()
    assert mode["mode"] == "ATTENDANCE"

    touch = client.prepare_touch("CARD1", "dummy", datetime.now().astimezone())
    assert touch["touch_token"] == "tok123"

    term_total = client.capture_term_total("CARD1", "dummy", datetime.now().astimezone())
    assert term_total["total_minutes"] == 75

    touch_error = client.capture_touch_error("invalid action", datetime.now().astimezone())
    assert touch_error["ok"] is True

    confirm = client.confirm_touch("tok123", "ENTER", datetime.now().astimezone())
    assert confirm["next_status"] == "IN_ROOM"
