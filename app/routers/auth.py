from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin_session import clear_admin_session, establish_admin_session
from app.config import get_settings
from app.deps import get_student_service
from app.kiosk import kiosk_state, KioskMode
from app.schemas.kiosk import CardCaptureResponse
from app.services.student_service import StudentService

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/admin/today", error: str | None = None):
    kiosk_state.set_mode(KioskMode.ADMIN_LOGIN)
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
        kiosk_state.clear_admin_login_capture()
        establish_admin_session(request, username)
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


@router.get("/api/login/latest-card", response_model=CardCaptureResponse | None)
def get_latest_login_card():
    capture = kiosk_state.get_latest_admin_login_capture()
    if capture is None:
        return None
    return CardCaptureResponse(
        card_id=capture.card_id,
        reader_name=capture.reader_name,
        detected_at=capture.detected_at,
    )


@router.post("/login/touch", response_class=HTMLResponse)
def login_by_touch(
    request: Request,
    card_id: str = Form(...),
    next: str = Form("/admin/today"),
    student_service: StudentService = Depends(get_student_service),
):
    kiosk_state.clear_admin_login_capture()
    student = student_service.get_by_card_id(card_id)
    if student is not None and student.is_admin and student.is_active:
        establish_admin_session(request, f"card:{student.student_code}")
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
    kiosk_state.clear_admin_login_capture()
    clear_admin_session(request)
    return RedirectResponse(url="/login", status_code=303)
