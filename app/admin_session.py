from __future__ import annotations

import time

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings


settings = get_settings()


def _session_expired(request: Request) -> bool:
    last_seen = request.session.get("admin_last_seen_at")
    if last_seen is None:
        return False
    return (time.time() - float(last_seen)) > settings.session_max_age_seconds


def _touch_session(request: Request) -> None:
    request.session["admin_last_seen_at"] = time.time()


def establish_admin_session(request: Request, username: str) -> None:
    request.session["admin_authenticated"] = True
    request.session["admin_username"] = username
    _touch_session(request)


def clear_admin_session(request: Request) -> None:
    request.session.clear()


def require_admin_page_auth(request: Request):
    if request.session.get("admin_authenticated") and _session_expired(request):
        clear_admin_session(request)
    if not request.session.get("admin_authenticated"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    _touch_session(request)
    return None


def require_admin_api_auth(request: Request) -> None:
    if request.session.get("admin_authenticated") and _session_expired(request):
        clear_admin_session(request)
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=401, detail="管理者ログインが必要です")
    _touch_session(request)
