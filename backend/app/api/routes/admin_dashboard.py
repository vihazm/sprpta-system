"""Administrator dashboard: GET /api/admin/dashboard (admin only)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.schemas.admin_dashboard import AdminDashboard
from app.services import admin_dashboard_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboard, dependencies=[Depends(require_roles("admin"))])
def dashboard(response: Response, db: Session = Depends(get_db)) -> AdminDashboard:
    response.headers["Cache-Control"] = "no-store"
    return admin_dashboard_service.build_dashboard(db)
