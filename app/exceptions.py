from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.exceptions import (
    DuplicateCardIdError,
    DuplicateStudentCodeError,
    InactiveStudentError,
    InvalidActionError,
    ServiceError,
    StudentNotFoundError,
    TouchTokenExpiredError,
    TouchTokenNotFoundError,
    UnknownCardError,
)


def map_service_error(err: ServiceError) -> tuple[int, str]:
    if isinstance(err, (DuplicateStudentCodeError, DuplicateCardIdError)):
        return 409, str(err)
    if isinstance(err, StudentNotFoundError):
        return 404, str(err)
    if isinstance(err, UnknownCardError):
        return 404, str(err)
    if isinstance(err, InactiveStudentError):
        return 403, str(err)
    if isinstance(err, TouchTokenNotFoundError):
        return 404, str(err)
    if isinstance(err, TouchTokenExpiredError):
        return 410, str(err)
    if isinstance(err, InvalidActionError):
        return 400, str(err)
    return 500, "内部サービスエラー"


def install_exception_handlers(app):
    templates = Jinja2Templates(directory="app/templates")

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        status_code, message = map_service_error(exc)
        # APIはJSON、ページはHTMLで返す
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=status_code, content={"detail": message})
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "エラー", "message": message},
            status_code=status_code,
        )

    @app.exception_handler(Exception)
    async def fallback_error_handler(request: Request, exc: Exception):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=500, content={"detail": "内部サーバーエラー"})
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "エラー", "message": "予期しないエラーが発生しました"},
            status_code=500,
        )
