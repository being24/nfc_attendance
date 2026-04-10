from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.domain.enums import AttendanceAction
from app.domain.time_utils import now_jst
from app.deps import get_attendance_service, get_student_service
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.attendance_service import AttendanceService
from app.services.exceptions import (
    DuplicateCardIdError,
    DuplicateStudentCodeError,
    InvalidActionError,
    StudentNotFoundError,
)
from app.services.student_service import StudentService

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")

ACTION_LABELS = {
    AttendanceAction.ENTER.value: "入室",
    AttendanceAction.LEAVE_TEMP.value: "一時退出",
    AttendanceAction.RETURN.value: "再入室",
    AttendanceAction.LEAVE_FINAL.value: "退出",
}

STATUS_LABELS = {
    "OUTSIDE": "室外",
    "IN_ROOM": "在室",
    "OUT_ON_BREAK": "一時退出中",
}

SOURCE_LABELS = {
    "reader": "リーダー",
    "admin_correction": "管理者補正",
}


def require_admin_page_auth(request: Request):
    if not request.session.get("admin_authenticated"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return None


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    attendance_service: AttendanceService = Depends(get_attendance_service),
):
    today = attendance_service.get_today_attendance()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "打刻待受",
            "action_options": [a.value for a in AttendanceAction],
            "in_room": today.in_room,
            "recent_events": today.events[:5],
            "unknown_card_alert": today.unknown_card_alert,
            "event_type_labels": ACTION_LABELS,
        },
    )


@router.post("/touch/manual", response_class=HTMLResponse)
@router.post("/touch/simulate", response_class=HTMLResponse)
def manual_touch(
    request: Request,
    card_id: str = Form(...),
    action: str = Form("auto"),
    attendance_service: AttendanceService = Depends(get_attendance_service),
):
    now = now_jst()
    touch = attendance_service.prepare_touch(
        card_id=card_id,
        reader_name="web-touch-panel",
        detected_at=now,
    )
    allowed = [a.value for a in touch.allowed_actions]
    chosen = allowed[0] if action == "auto" else action
    if chosen not in allowed:
        raise InvalidActionError(f"許可されていない操作です（許可: {', '.join(allowed)}）")
    confirm = attendance_service.confirm_touch(
        touch_token=touch.touch_token,
        action=AttendanceAction(chosen),
        now=now_jst(),
    )
    chosen_label = ACTION_LABELS.get(chosen, chosen)
    next_status_label = STATUS_LABELS.get(confirm.next_status.value, confirm.next_status.value)
    return templates.TemplateResponse(
        request,
        "touch_result.html",
        {
            "title": "打刻完了",
            "message": f"カード {card_id} を「{chosen_label}」で処理しました（次状態: {next_status_label}）",
            "lock_alert_required": confirm.lock_alert_required,
        },
    )


@router.get("/error", response_class=HTMLResponse)
def error_page(request: Request, message: str = Query("エラーが発生しました")):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"title": "エラー", "message": message},
        status_code=400,
    )


@router.get("/touch_result", response_class=HTMLResponse)
def touch_result_page(
    request: Request,
    title: str = Query("打刻完了"),
    message: str = Query("処理が完了しました"),
    lock_alert_required: bool = Query(False),
):
    return templates.TemplateResponse(
        request,
        "touch_result.html",
        {
            "title": title,
            "message": message,
            "lock_alert_required": lock_alert_required,
        },
    )


@router.post("/student/term-total", response_class=HTMLResponse)
def student_term_total_page(
    request: Request,
    card_id: str = Form(...),
    attendance_service: AttendanceService = Depends(get_attendance_service),
):
    student, total_minutes, start, end = attendance_service.get_current_term_total_minutes_by_card(card_id=card_id, now=now_jst())
    hours = total_minutes // 60
    minutes = total_minutes % 60
    period = f"{start.strftime('%Y-%m-%d')} 〜 {end.strftime('%Y-%m-%d')}"
    return templates.TemplateResponse(
        request,
        "touch_result.html",
        {
            "title": "今期通算在室時間",
            "message": (
                f"{student.student_code} {student.name} の今期通算在室時間: "
                f"{hours}時間{minutes}分（{total_minutes}分） / 期間: {period}"
            ),
            "lock_alert_required": False,
        },
    )


@router.get("/admin/today", response_class=HTMLResponse)
def admin_today_page(
    request: Request,
    attendance_service: AttendanceService = Depends(get_attendance_service),
):
    today = attendance_service.get_today_attendance()
    return templates.TemplateResponse(
        request,
        "admin_today.html",
        {
            "title": "本日在室一覧",
            "in_room": today.in_room,
            "status_labels": STATUS_LABELS,
        },
    )


@router.get("/admin/students", response_class=HTMLResponse)
def admin_students_page(
    request: Request,
    student_service: StudentService = Depends(get_student_service),
):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    students = student_service.list_students(include_inactive=True)
    return templates.TemplateResponse(
        request,
        "admin_students.html",
        {
            "title": "学生一覧",
            "students": students,
        },
    )


@router.get("/admin/students/new", response_class=HTMLResponse)
def admin_student_new_form(request: Request):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "admin_student_form.html",
        {
            "title": "学生登録",
            "form_mode": "create",
            "student": None,
            "error": None,
        },
    )


@router.get("/admin/students/{student_id}/edit", response_class=HTMLResponse)
def admin_student_edit_form(
    request: Request,
    student_id: int,
    student_service: StudentService = Depends(get_student_service),
):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    try:
        student = student_service.get_student(student_id)
    except StudentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return templates.TemplateResponse(
        request,
        "admin_student_form.html",
        {
            "title": "学生編集",
            "form_mode": "edit",
            "student": student,
            "error": None,
        },
    )


@router.post("/admin/students", response_class=HTMLResponse)
def admin_student_create(
    request: Request,
    student_code: str = Form(...),
    name: str = Form(...),
    card_id: str = Form(...),
    note: str = Form(""),
    student_service: StudentService = Depends(get_student_service),
):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    try:
        student_service.register_student(
            StudentCreate(
                student_code=student_code,
                name=name,
                card_id=card_id,
                note=note or None,
            )
        )
    except (DuplicateStudentCodeError, DuplicateCardIdError) as e:
        return templates.TemplateResponse(
            request,
            "admin_student_form.html",
            {
                "title": "学生登録",
                "form_mode": "create",
                "student": None,
                "error": str(e),
            },
            status_code=409,
        )

    return RedirectResponse(url="/admin/students", status_code=303)


@router.post("/admin/students/{student_id}", response_class=HTMLResponse)
def admin_student_update(
    request: Request,
    student_id: int,
    name: str = Form(...),
    card_id: str = Form(...),
    note: str = Form(""),
    is_active: bool = Form(False),
    student_service: StudentService = Depends(get_student_service),
):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    try:
        student_service.update_student(
            student_id,
            StudentUpdate(name=name, card_id=card_id, note=note or None, is_active=is_active),
        )
    except StudentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (DuplicateStudentCodeError, DuplicateCardIdError) as e:
        student = student_service.get_student(student_id)
        return templates.TemplateResponse(
            request,
            "admin_student_form.html",
            {
                "title": "学生編集",
                "form_mode": "edit",
                "student": student,
                "error": str(e),
            },
            status_code=409,
        )

    return RedirectResponse(url="/admin/students", status_code=303)


@router.get("/admin/events", response_class=HTMLResponse)
def admin_events_page(
    request: Request,
    attendance_service: AttendanceService = Depends(get_attendance_service),
):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    today = attendance_service.get_today_attendance()
    return templates.TemplateResponse(
        request,
        "admin_events.html",
        {
            "title": "本日イベント一覧",
            "events": today.events,
            "event_type_labels": ACTION_LABELS,
            "source_labels": SOURCE_LABELS,
        },
    )


@router.get("/admin/export", response_class=HTMLResponse)
def admin_export_page(request: Request):
    redirect = require_admin_page_auth(request)
    if redirect:
        return redirect
    now = now_jst()
    semester_year = now.year if now.month >= 4 else now.year - 1
    semester = 1 if 4 <= now.month <= 9 else 2
    return templates.TemplateResponse(
        request,
        "admin_export.html",
        {
            "title": "CSV出力",
            "year": now.year,
            "month": now.month,
            "semester_year": semester_year,
            "semester": semester,
        },
    )
