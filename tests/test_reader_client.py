from datetime import datetime

import httpx

from reader.client import ReaderApiClient


def test_reader_client_prepare_and_confirm(monkeypatch):
    routes = {
        "http://localhost:8000/api/reader/touches": {
            "touch_token": "tok123",
            "allowed_actions": ["ENTER"],
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
    touch = client.prepare_touch("CARD1", "dummy", datetime.now().astimezone())
    assert touch["touch_token"] == "tok123"

    confirm = client.confirm_touch("tok123", "ENTER", datetime.now().astimezone())
    assert confirm["next_status"] == "IN_ROOM"
