from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from app.env import load_project_dotenv
from reader.client import ReaderApiClient
from reader.debounce import Debouncer


load_project_dotenv()


def configure_logger() -> logging.Logger:
    logger = logging.getLogger("reader")
    if logger.handlers:
        return logger

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile_path = log_dir / "reader.log"

    handler = RotatingFileHandler(
        filename=logfile_path,
        encoding="utf-8",
        maxBytes=32 * 1024,
        backupCount=5,
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}",
        dt_fmt,
        style="{",
    )
    handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ダミーNFCリーダークライアント")
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
            raise RuntimeError("サーバーから許可操作が返されませんでした")
        return allowed_actions[0]
    if requested not in allowed_actions:
        raise RuntimeError(f"指定された操作 {requested} は許可されていません（許可: {allowed_actions}）")
    return requested


def run_once(client: ReaderApiClient, debouncer: Debouncer, card_id: str, reader_name: str, action: str):
    now = datetime.now().astimezone()
    if not debouncer.allow(card_id):
        logger.info("skip cooldown card_id=%s reader_name=%s detected_at=%s", card_id, reader_name, now.isoformat())
        return

    try:
        touch = client.prepare_touch(card_id=card_id, reader_name=reader_name, detected_at=now)
        allowed = touch.get("allowed_actions", [])
        chosen = choose_action(action, allowed)
        confirm = client.confirm_touch(touch_token=touch["touch_token"], action=chosen, now=datetime.now().astimezone())
    except httpx.HTTPError:
        logger.exception("reader api error card_id=%s reader_name=%s", card_id, reader_name)
        raise
    except Exception:
        logger.exception("reader processing error card_id=%s reader_name=%s", card_id, reader_name)
        raise

    logger.info(
        "touch processed card_id=%s reader_name=%s action=%s next_status=%s lock_alert_required=%s",
        card_id,
        reader_name,
        chosen,
        confirm.get("next_status"),
        confirm.get("lock_alert_required"),
    )


def main() -> int:
    args = parse_args()
    client = ReaderApiClient(base_url=args.base_url, reader_token=args.reader_token)
    debouncer = Debouncer(cooldown_seconds=args.cooldown)
    logger.info(
        "reader started base_url=%s reader_name=%s mode=%s interval=%s count=%s cooldown=%s",
        args.base_url,
        args.reader_name,
        "loop" if args.loop else "count",
        args.interval,
        args.count,
        args.cooldown,
    )

    if args.loop:
        try:
            while True:
                run_once(client, debouncer, args.card_id, args.reader_name, args.action)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("reader stopped by keyboard interrupt")
            return 0

    count = max(1, args.count)
    try:
        for _ in range(count):
            run_once(client, debouncer, args.card_id, args.reader_name, args.action)
            if count > 1:
                time.sleep(args.interval)
    finally:
        logger.info("reader finished")

    return 0


if __name__ == "__main__":
    sys.exit(main())
