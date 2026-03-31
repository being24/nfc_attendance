from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db import Base, engine
from app.exceptions import install_exception_handlers
import app.models  # noqa: F401
from app.routers import (
    admin_router,
    attendance_router,
    auth_router,
    export_router,
    pages_router,
    reader_router,
    students_router,
)

app = FastAPI(title="NFC Attendance API")
settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

app.include_router(reader_router)
app.include_router(students_router)
app.include_router(attendance_router)
app.include_router(admin_router)
app.include_router(export_router)
app.include_router(pages_router)
app.include_router(auth_router)
install_exception_handlers(app)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
