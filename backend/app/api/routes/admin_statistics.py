"""Masked statistics and reports: /api/admin/statistics (admin only)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import error, require_roles
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID
from app.schemas.statistics import StatisticsFilters, StatisticsOut
from app.services import statistics_service

router = APIRouter(prefix="/api/admin/statistics", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


@router.get("", response_model=StatisticsOut)
def statistics(
    response: Response,
    date_from: date | None = None,
    date_to: date | None = None,
    area_id: int | None = Query(None, ge=1, le=MAX_ID),
    category_id: int | None = Query(None, ge=1, le=MAX_ID),
    severity_id: int | None = Query(None, ge=1, le=MAX_ID),
    medium_id: int | None = Query(None, ge=1, le=MAX_ID),
    db: Session = Depends(get_db),
) -> StatisticsOut:
    if date_from and date_to and date_from > date_to:
        raise error(422, "bad_period", "The start date must be on or before the end date.")
    response.headers["Cache-Control"] = "no-store"
    filters = StatisticsFilters(
        date_from=date_from,
        date_to=date_to,
        area_id=area_id,
        category_id=category_id,
        severity_id=severity_id,
        medium_id=medium_id,
    )
    return statistics_service.statistics(db, filters)
