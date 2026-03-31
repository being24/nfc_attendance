import time


class Debouncer:
    def __init__(self, cooldown_seconds: float = 2.0):
        self.cooldown_seconds = cooldown_seconds
        self._last_seen: dict[str, float] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        prev = self._last_seen.get(key)
        if prev is None or (now - prev) >= self.cooldown_seconds:
            self._last_seen[key] = now
            return True
        return False
