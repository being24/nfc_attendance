from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import get_correction_service
from app.schemas.admin import CorrectionRequest
from app.services.correction_service import CorrectionService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin_api_auth(request: Request) -> None:
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=401, detail="管理者ログインが必要です")


@router.post("/corrections")
def create_correction(
    request: Request,
    payload: CorrectionRequest,
    service: CorrectionService = Depends(get_correction_service),
):
    require_admin_api_auth(request)
    event_id = service.add_correction(payload)
    return {"event_id": event_id}
