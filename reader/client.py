from __future__ import annotations

from datetime import datetime

import httpx


class ReaderApiClient:
    def __init__(self, base_url: str, reader_token: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.reader_token = reader_token
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Reader-Token": self.reader_token}

    def prepare_touch(self, card_id: str, reader_name: str | None, detected_at: datetime) -> dict:
        payload = {
            "card_id": card_id,
            "reader_name": reader_name,
            "detected_at": detected_at.isoformat(),
        }
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/reader/touches", json=payload, headers=self._headers)
            res.raise_for_status()
            return res.json()

    def confirm_touch(self, touch_token: str, action: str, now: datetime) -> dict:
        payload = {"action": action, "now": now.isoformat()}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/api/reader/touches/{touch_token}/confirm",
                json=payload,
                headers=self._headers,
            )
            res.raise_for_status()
            return res.json()
