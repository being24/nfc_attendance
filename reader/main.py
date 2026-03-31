from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

from reader.client import ReaderApiClient
from reader.debounce import Debouncer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dummy NFC reader client")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--reader-token", default=os.getenv("READER_TOKEN", "dev-reader-token"))
    parser.add_argument("--reader-name", default=os.getenv("READER_NAME", "dummy-reader"))
    parser.add_argument("--card-id", default="DUMMY-CARD-001")
    parser.add_argument("--action", choices=["ENTER", "LEAVE_TEMP", "RETURN", "LEAVE_FINAL", "auto"], default="auto")
    parser.add_argument("--cooldown", type=float, default=2.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--loop", action="store_true")
    return parser.parse_args()


def choose_action(requested: str, allowed_actions: list[str]) -> str:
    if requested == "auto":
        if not allowed_actions:
            raise RuntimeError("No allowed actions returned from server")
        return allowed_actions[0]
    if requested not in allowed_actions:
        raise RuntimeError(f"Requested action {requested} not allowed. allowed={allowed_actions}")
    return requested


def run_once(client: ReaderApiClient, debouncer: Debouncer, card_id: str, reader_name: str, action: str):
    now = datetime.now().astimezone()
    if not debouncer.allow(card_id):
        print(f"[SKIP] cooldown active for card {card_id}")
        return

    touch = client.prepare_touch(card_id=card_id, reader_name=reader_name, detected_at=now)
    allowed = touch.get("allowed_actions", [])
    chosen = choose_action(action, allowed)
    confirm = client.confirm_touch(touch_token=touch["touch_token"], action=chosen, now=datetime.now().astimezone())

    print(f"[OK] card={card_id} action={chosen} next={confirm.get('next_status')} lock_alert={confirm.get('lock_alert_required')}")


def main() -> int:
    args = parse_args()
    client = ReaderApiClient(base_url=args.base_url, reader_token=args.reader_token)
    debouncer = Debouncer(cooldown_seconds=args.cooldown)

    if args.loop:
        print("[INFO] dummy reader loop started. Ctrl+C to stop")
        try:
            while True:
                run_once(client, debouncer, args.card_id, args.reader_name, args.action)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[INFO] stopped")
            return 0

    count = max(1, args.count)
    for _ in range(count):
        run_once(client, debouncer, args.card_id, args.reader_name, args.action)
        if count > 1:
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())
