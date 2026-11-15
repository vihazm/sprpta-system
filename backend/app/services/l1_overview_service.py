"""The lower cards of the Level 1 dashboard, as PostgreSQL aggregates over the signed-in officer's own complaints."""

from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import Area, Complaint, ComplaintMedium, Severity, User, Vehicle
from app.schemas.l1_overview import (
    AreaCount,
    BusiestMedium,
    ForwardedRow,
    OverviewOut,
    SeverityCount,
    SourceRow,
    TransportCounts,
)
from app.services.auth_service import Principal

RECENT_LIMIT = 4
SEVERITY_BY_RANK = {1: "critical", 2: "high", 3: "medium", 4: "low"}  # the four levels, most serious first


def overview(db: Session, officer: Principal) -> OverviewOut:
    now = datetime.now(LOCAL)
    today = datetime.combine(now.date(), time.min, LOCAL)
    monday = today - timedelta(days=today.weekday())
    first = today.replace(day=1)
    mine = Complaint.entered_by_user_id == officer.id
    count = func.count(Complaint.id)

    def by_medium(since: datetime):
        return db.execute(
            select(ComplaintMedium.name, count)
            .select_from(Complaint)
            .outerjoin(ComplaintMedium, ComplaintMedium.id == Complaint.medium_id)
            .where(mine, Complaint.created_at >= since)
            .group_by(ComplaintMedium.name)
            .order_by(count.desc(), ComplaintMedium.name)
        ).all()

    sources = [SourceRow(label=name or "Not recorded", count=n) for name, n in by_medium(first)]
    week = by_medium(monday)
    busiest = BusiestMedium(
        medium=(week[0][0] or "Not recorded") if week else None,
        count=week[0][1] if week else 0,
        total=sum(n for _name, n in week),
    )

    forwarded_this_month = dict(
        db.execute(
            select(Complaint.area_id, count)
            .where(mine, Complaint.forwarded_at >= first, Complaint.area_id.is_not(None))
            .group_by(Complaint.area_id)
        ).all()
    )
    covered = set(
        db.scalars(select(User.area_id).where(User.role == UserRole.L2, User.is_active, User.area_id.is_not(None)))
    )
    areas = [
        AreaCount(name=a.name, count=forwarded_this_month.get(a.id, 0), has_officer=a.id in covered)
        for a in db.scalars(select(Area).order_by(Area.id))
    ]

    types = dict(
        db.execute(
            select(Vehicle.vehicle_type, count)
            .select_from(Complaint)
            .join(Vehicle, Vehicle.id == Complaint.vehicle_id)
            .where(mine, Complaint.created_at >= first)
            .group_by(Vehicle.vehicle_type)
        ).all()
    )
    no_vehicle = db.scalar(select(count).where(mine, Complaint.created_at >= first, Complaint.vehicle_id.is_(None))) or 0
    ranks = dict(
        db.execute(
            select(Severity.rank, count)
            .select_from(Complaint)
            .join(Severity, Severity.id == Complaint.severity_id)
            .where(mine, Complaint.created_at >= first)
            .group_by(Severity.rank)
        ).all()
    )

    latest = db.execute(
        select(Complaint, Area.name, Severity.rank)
        .outerjoin(Area, Area.id == Complaint.area_id)
        .outerjoin(Severity, Severity.id == Complaint.severity_id)
        .where(mine, Complaint.forwarded_at.is_not(None))
        .order_by(Complaint.forwarded_at.desc(), Complaint.id.desc())
        .limit(RECENT_LIMIT)
    ).all()

    return OverviewOut(
        month_total=sum(s.count for s in sources),
        sources=sources,
        busiest_week=busiest,
        areas=areas,
        forwarded_total=sum(a.count for a in areas),
        transport=TransportCounts(
            bus=types.get(VehicleType.BUS, 0), trishaw=types.get(VehicleType.TRISHAW, 0), unknown=no_vehicle
        ),
        severity=[SeverityCount(severity=name, count=ranks.get(rank, 0)) for rank, name in SEVERITY_BY_RANK.items()],
        forwarded=[
            ForwardedRow(
                id=c.id,
                reference_number=c.reference_number,
                title=c.subject,
                severity=SEVERITY_BY_RANK.get(rank),
                area_name=area,
                forwarded_at=c.forwarded_at,
                has_contact=bool(c.contact_phone or c.contact_email),
            )
            for c, area, rank in latest
        ],
    )
