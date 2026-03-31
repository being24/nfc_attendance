from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _allowed_admin_cards() -> set[str]:
    return {c.strip() for c in settings.admin_card_ids.split(",") if c.strip()}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/admin/today", error: str | None = None):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": "ログイン",
            "next": next,
            "error": error,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/today"),
):
    if username == settings.admin_username and password == settings.admin_password:
        request.session["admin_authenticated"] = True
        request.session["admin_username"] = username
        return RedirectResponse(url=next or "/admin/today", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": "ログイン",
            "next": next,
            "error": "ユーザー名またはパスワードが正しくありません",
        },
        status_code=401,
    )


@router.post("/login/touch", response_class=HTMLResponse)
def login_by_touch(
    request: Request,
    card_id: str = Form(...),
    next: str = Form("/admin/today"),
):
    if card_id in _allowed_admin_cards():
        request.session["admin_authenticated"] = True
        request.session["admin_username"] = f"card:{card_id}"
        return RedirectResponse(url=next or "/admin/today", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": "ログイン",
            "next": next,
            "error": "管理者カードではありません",
        },
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
