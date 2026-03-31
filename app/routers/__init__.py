from app.routers.admin import router as admin_router
from app.routers.attendance import router as attendance_router
from app.routers.auth import router as auth_router
from app.routers.export import router as export_router
from app.routers.pages import router as pages_router
from app.routers.reader import router as reader_router
from app.routers.students import router as students_router

__all__ = [
    "admin_router",
    "attendance_router",
    "auth_router",
    "export_router",
    "pages_router",
    "reader_router",
    "students_router",
]
