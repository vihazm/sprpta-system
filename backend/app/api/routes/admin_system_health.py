"""System health: /api/admin/system-health (admin only)."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.schemas.system_health import SystemHealth
from app.services import health_check_service, system_health_service

router = APIRouter(prefix="/api/admin/system-health", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


@router.get("", response_model=SystemHealth)
def system_health(response: Response, db: Session = Depends(get_db)) -> SystemHealth:
    response.headers["Cache-Control"] = "no-store"
    return system_health_service.build_system_health(db)


@router.post("/checks", response_model=SystemHealth)
async def run_checks(request: Request, response: Response, db: Session = Depends(get_db)) -> SystemHealth:
    """Checks every service now instead of waiting for the next minute."""
    response.headers["Cache-Control"] = "no-store"
    await health_check_service.run_checks(request.app)
    return system_health_service.build_system_health(db)
