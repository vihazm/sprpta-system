"""Dashboard analytics: PostgreSQL aggregates over the officer's own complaints. Nothing is cached or hard-coded."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus, DuplicateLinkType
from app.models import Area, Complaint, ComplaintCategory, DuplicateCheck, RouteStand
from app.schemas.l1_analytics import AnalyticsOut, CountRow, MonthRow
from app.services.auth_service import Principal

FAILED = ("not_found", "not_operated", "trip_cancelled", "unverified")
NON_OPERATING = ("not_operated", "trip_cancelled")
TOP_ROUTES = 10


def _rows(db: Session, name_column, join_model, join_on, mine, limit: int | None = None, empty: str = "None") -> list[CountRow]:
    count = func.count(Complaint.id)
    query = (
        select(join_model.id, name_column, count)
        .select_from(Complaint)
        .outerjoin(join_model, join_on)
        .where(mine)
        .group_by(join_model.id, name_column)
        .order_by(count.desc(), name_column)
    )
    if limit:
        query = query.limit(limit)
    return [CountRow(id=i, name=n or empty, count=c) for i, n, c in db.execute(query).all()]


def analytics(db: Session, officer: Principal) -> AnalyticsOut:
    mine = Complaint.entered_by_user_id == officer.id
    count = func.count(Complaint.id)
    month = func.to_char(Complaint.complaint_date, "YYYY-MM")
    by_month = [
        MonthRow(month=m or "unknown", count=c)
        for m, c in db.execute(select(month, count).where(mine).group_by(month).order_by(month.nulls_last())).all()
    ]
    duplicate = (
        select(DuplicateCheck.complaint_id)
        .where(DuplicateCheck.link_type == DuplicateLinkType.DUPLICATE_OF)
    )
    return AnalyticsOut(
        total=db.scalar(select(count).where(mine)) or 0,
        by_category=_rows(db, ComplaintCategory.name, ComplaintCategory, Complaint.category_id == ComplaintCategory.id, mine, empty="No category"),
        by_route=_rows(db, RouteStand.name, RouteStand, Complaint.route_stand_id == RouteStand.id, and_(mine, Complaint.route_stand_id.is_not(None)), TOP_ROUTES, "No route"),  # a complaint with no route is not a route
        by_district=_rows(db, Area.name, Area, Complaint.area_id == Area.id, mine, empty="Not assigned yet"),
        by_month=by_month,
        duplicates=db.scalar(select(count).where(mine, Complaint.id.in_(duplicate))) or 0,
        incomplete=db.scalar(select(count).where(mine, Complaint.status == ComplaintStatus.INCOMPLETE)) or 0,
        failed_verification=db.scalar(select(count).where(mine, Complaint.bus_verification.in_(FAILED))) or 0,
        non_operating=db.scalar(select(count).where(mine, Complaint.bus_verification.in_(NON_OPERATING))) or 0,
    )
