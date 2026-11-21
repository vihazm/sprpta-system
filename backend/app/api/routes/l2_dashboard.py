"""The Level 2 dashboard summary: /api/l2/dashboard (area officers only, own area only)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.l2_cases import DashboardOut
from app.services import l2_case_service
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError

router = APIRouter(prefix="/api/l2/dashboard", tags=["l2"], dependencies=[Depends(require_roles("l2"))])


@router.get("", response_model=DashboardOut)
def dashboard(
    response: Response, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> DashboardOut:
    response.headers["Cache-Control"] = "no-store"
    try:
        return l2_case_service.dashboard(db, officer)
    except ComplaintError as exc:
        raise error(exc.status, exc.code, exc.message) from None
