from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time
from datetime import datetime
import json
from pathlib import Path
from typing import Callable

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

ACTION_LABELS = {
    "ENTER": "入室",
    "LEAVE_TEMP": "一時退出",
    "RETURN": "再入室",
    "LEAVE_FINAL": "退出",
}


class InvalidPreferredActionError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ダミーNFCリーダークライアント")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--reader-token", default=os.getenv("READER_TOKEN", "dev-reader-token"))
    parser.add_argument("--reader-name", default=os.getenv("READER_NAME"))
    parser.add_argument("--card-id")
    parser.add_argument("--action", choices=["ENTER", "LEAVE_TEMP", "RETURN", "LEAVE_FINAL", "auto"], default="auto")
    parser.add_argument("--cooldown", type=float, default=2.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--device-keyword", default=os.getenv("READER_DEVICE_KEYWORD", "SONY FeliCa"))
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def resolve_reader_name(args: argparse.Namespace) -> str:
    if args.reader_name:
        return args.reader_name
    if args.card_id:
        return "dummy-reader"
    return "real-reader"


def choose_action(requested: str, allowed_actions: list[str], preferred_action: str | None = None) -> str:
    if requested == "auto":
        if not allowed_actions:
            raise RuntimeError("サーバーから許可操作が返されませんでした")
        if preferred_action is not None:
            if preferred_action not in allowed_actions:
                preferred_label = ACTION_LABELS.get(preferred_action, preferred_action)
                allowed_labels = [ACTION_LABELS.get(action, action) for action in allowed_actions]
                raise InvalidPreferredActionError(
                    f"選択中の操作「{preferred_label}」はこのカードでは使えません（許可: {', '.join(allowed_labels)}）"
                )
            return preferred_action
        return allowed_actions[0]
    if requested not in allowed_actions:
        raise RuntimeError(f"指定された操作 {requested} は許可されていません（許可: {allowed_actions}）")
    return requested


def summarize_http_error(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    detail = ""
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        detail_value = payload.get("detail")
        if isinstance(detail_value, str):
            detail = detail_value
    if not detail:
        text = response.text.strip()
        detail = text[:200] if text else "detail unavailable"
    return f"status={response.status_code} detail={detail}"


def run_once(client: ReaderApiClient, debouncer: Debouncer, card_id: str, reader_name: str, action: str):
    now = datetime.now().astimezone()
    if not debouncer.allow(card_id):
        logger.info("skip cooldown card_id=%s reader_name=%s detected_at=%s", card_id, reader_name, now.isoformat())
        return

    try:
        kiosk_mode = client.get_kiosk_mode().get("mode", "ATTENDANCE")
        if kiosk_mode == "ADMIN_LOGIN":
            client.capture_admin_login_card(card_id=card_id, reader_name=reader_name, detected_at=now)
            logger.info("card captured for admin login card_id=%s reader_name=%s", card_id, reader_name)
            return
        if kiosk_mode == "STUDENT_REGISTER":
            client.capture_student_card(card_id=card_id, reader_name=reader_name, detected_at=now)
            logger.info("card captured for student registration card_id=%s reader_name=%s", card_id, reader_name)
            return
        touch_panel_action = client.get_touch_panel_action().get("selected_action", "ENTER")
        if touch_panel_action == "TERM_TOTAL":
            result = client.capture_term_total(card_id=card_id, reader_name=reader_name, detected_at=now)
            logger.info(
                "term total captured card_id=%s reader_name=%s student_code=%s total_minutes=%s",
                card_id,
                reader_name,
                result.get("student_code"),
                result.get("total_minutes"),
            )
            return
        touch = client.prepare_touch(card_id=card_id, reader_name=reader_name, detected_at=now)
        allowed = touch.get("allowed_actions", [])
        preferred_action = touch.get("preferred_action")
        chosen = choose_action(action, allowed, preferred_action=preferred_action)
        confirm = client.confirm_touch(touch_token=touch["touch_token"], action=chosen, now=datetime.now().astimezone())
    except InvalidPreferredActionError as exc:
        client.capture_touch_error(str(exc), detected_at=now)
        logger.warning("reader invalid selected action card_id=%s reader_name=%s error=%s", card_id, reader_name, exc)
        return
    except httpx.HTTPStatusError as exc:
        logger.error(
            "reader api error card_id=%s reader_name=%s %s",
            card_id,
            reader_name,
            summarize_http_error(exc),
        )
        raise
    except httpx.HTTPError:
        logger.exception("reader transport error card_id=%s reader_name=%s", card_id, reader_name)
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


def build_card_event_handler(
    client: ReaderApiClient,
    debouncer: Debouncer,
    reader_name: str,
    action: str,
) -> Callable[[str, str | None, Exception | None], None]:
    def handle_event(event_type: str, card_id: str | None, error: Exception | None = None) -> None:
        if error is not None:
            logger.error("reader card event error reader_name=%s error=%s", reader_name, error)
            return
        if event_type != "insert" or not card_id:
            return
        try:
            run_once(client, debouncer, card_id, reader_name, action)
        except httpx.HTTPError:
            return
        except Exception:
            logger.exception("failed to process card event card_id=%s reader_name=%s", card_id, reader_name)

    return handle_event


def run_dummy_mode(args: argparse.Namespace, client: ReaderApiClient, debouncer: Debouncer) -> int:
    reader_name = resolve_reader_name(args)
    logger.info(
        "reader started base_url=%s reader_name=%s mode=%s interval=%s count=%s cooldown=%s",
        args.base_url,
        reader_name,
        "loop" if args.loop else "count",
        args.interval,
        args.count,
        args.cooldown,
    )
    if args.loop:
        try:
            while True:
                run_once(client, debouncer, args.card_id, reader_name, args.action)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("reader stopped by keyboard interrupt")
            return 0

    count = max(1, args.count)
    try:
        for _ in range(count):
            run_once(client, debouncer, args.card_id, reader_name, args.action)
            if count > 1:
                time.sleep(args.interval)
    finally:
        logger.info("reader finished")

    return 0


def run_real_mode(args: argparse.Namespace, client: ReaderApiClient, debouncer: Debouncer) -> int:
    from reader.nfc import NFCMonitor, NFCReaderError

    reader_name = resolve_reader_name(args)
    try:
        monitor = NFCMonitor(
            reader_name_keyword=args.device_keyword,
            callback=build_card_event_handler(client, debouncer, reader_name, args.action),
        )
    except NFCReaderError:
        logger.exception("failed to start real reader monitor device_keyword=%s", args.device_keyword)
        return 1

    logger.info(
        "reader started base_url=%s reader_name=%s mode=monitor device_keyword=%s cooldown=%s",
        args.base_url,
        reader_name,
        args.device_keyword,
        args.cooldown,
    )
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("reader stopped by keyboard interrupt")
        return 0
    finally:
        monitor.stop()


def main() -> int:
    args = parse_args()
    client = ReaderApiClient(base_url=args.base_url, reader_token=args.reader_token)
    debouncer = Debouncer(cooldown_seconds=args.cooldown)
    try:
        if args.card_id:
            return run_dummy_mode(args, client, debouncer)
        return run_real_mode(args, client, debouncer)
    except httpx.HTTPError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
