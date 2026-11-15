"""The Level 1 dashboard summary: /api/l1/dashboard (office staff only)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.l1_analytics import AnalyticsOut
from app.schemas.l1_dashboard import DashboardOut
from app.schemas.l1_overview import OverviewOut
from app.services import l1_analytics_service, l1_dashboard_service, l1_overview_service
from app.services.auth_service import Principal

router = APIRouter(prefix="/api/l1/dashboard", tags=["l1"], dependencies=[Depends(require_roles("l1"))])


@router.get("", response_model=DashboardOut)
def dashboard(
    response: Response, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> DashboardOut:
    response.headers["Cache-Control"] = "no-store"
    return l1_dashboard_service.dashboard(db, officer)


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(
    response: Response, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> AnalyticsOut:
    """Complaints by category, route, district and month, and the duplicate / incomplete / failed-verification counts."""
    response.headers["Cache-Control"] = "no-store"
    return l1_analytics_service.analytics(db, officer)


@router.get("/overview", response_model=OverviewOut)
def overview(
    response: Response, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> OverviewOut:
    """The lower cards: sources, passed to Level 2, transport and severity, recently forwarded."""
    response.headers["Cache-Control"] = "no-store"
    return l1_overview_service.overview(db, officer)
