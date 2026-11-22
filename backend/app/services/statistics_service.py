"""Complaint statistics (UC-AD-06, F-60; the same measures as UI-L3-02 for Level 3).

Every figure is a SQL aggregate. Only registered complaints are counted: drafts and portal submissions still waiting
for Level 1 have not entered the case flow. The period is matched against the registration date, in local time.
The results hold counts and days only, never a name or a contact, so they are already masked for the administrator
and Level 3 can reuse this service as it is. "Team" statistics wait until the client defines a team.

Time targets are calendar days from registration, without the time a complaint spent Incomplete: a stage is on
time when it finished by the end of its target day (0 days means the same day).
"""

from datetime import datetime, time, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL, LOCAL_TIMEZONE
from app.models import Area, Complaint, ComplaintCategory, ComplaintMedium, Severity
from app.schemas.statistics import (
    CountRow,
    FilterOptions,
    Option,
    Overdue,
    Stage,
    StatisticsFilters,
    StatisticsOut,
    TargetRow,
)
from app.services.l2_case_service import overdue

# The statuses a registered complaint can have, in the order of the flow.
STATUSES = [s for s in ComplaintStatus if s not in (ComplaintStatus.DRAFT, ComplaintStatus.SUBMITTED)]
NOT_SET = "Not set"


def _conditions(f: StatisticsFilters) -> list:
    conditions = [Complaint.registered_at.is_not(None)]
    if f.date_from:
        conditions.append(Complaint.registered_at >= datetime.combine(f.date_from, time(), LOCAL))
    if f.date_to:
        conditions.append(Complaint.registered_at < datetime.combine(f.date_to + timedelta(days=1), time(), LOCAL))
    for column, value in (
        (Complaint.area_id, f.area_id),
        (Complaint.category_id, f.category_id),
        (Complaint.severity_id, f.severity_id),
        (Complaint.medium_id, f.medium_id),
    ):
        if value:
            conditions.append(column == value)
    return conditions


def _by(db: Session, name, model, on, conditions: list, *, order=None) -> list[CountRow]:
    count = func.count(Complaint.id)
    rows = db.execute(
        select(name, count)
        .select_from(Complaint)
        .outerjoin(model, on)
        .where(*conditions)
        .group_by(*([name] if order is None else [name, order]))
        .order_by(*([count.desc(), name] if order is None else [order.nulls_last()]))
    ).all()
    return [CountRow(key=key or NOT_SET, count=n) for key, n in rows]


def _stage(finished_at, target_days) -> tuple:
    finished_day = func.date(func.timezone(LOCAL_TIMEZONE, finished_at - Complaint.paused_total))
    due_day = func.date(func.timezone(LOCAL_TIMEZONE, Complaint.registered_at)) + target_days
    days = func.extract("epoch", finished_at - Complaint.registered_at - Complaint.paused_total) / 86400
    return func.count(finished_at), func.count().filter(finished_day <= due_day), func.avg(days)


def _days(value) -> float | None:
    return round(float(value), 1) if value is not None else None


def _time_targets(db: Session, f: StatisticsFilters, conditions: list) -> list[TargetRow]:
    query = (
        select(
            Severity.name,
            Severity.forward_days,
            Severity.decide_days,
            Severity.close_days,
            *_stage(Complaint.forwarded_at, Severity.forward_days),
            *_stage(Complaint.decided_at, Severity.decide_days),
            *_stage(Complaint.closed_at, Severity.close_days),
        )
        .select_from(Severity)
        .outerjoin(Complaint, and_(Complaint.severity_id == Severity.id, *conditions))
        .group_by(Severity.id)
        .order_by(Severity.rank)
    )
    if f.severity_id:
        query = query.where(Severity.id == f.severity_id)

    rows = []
    for name, *values in db.execute(query).all():
        targets, measures = values[:3], values[3:]  # three targets, then three figures per stage
        stages = [
            Stage(
                target_days=targets[i],
                finished=measures[3 * i],
                on_time=measures[3 * i + 1],
                average_days=_days(measures[3 * i + 2]),
            )
            for i in range(3)
        ]
        rows.append(TargetRow(severity=name, forward=stages[0], decide=stages[1], close=stages[2]))

    def total(stage: str) -> Stage:
        parts = [getattr(row, stage) for row in rows]
        finished = sum(p.finished for p in parts)
        weighted = sum(p.average_days * p.finished for p in parts if p.average_days is not None)
        return Stage(
            target_days=None,
            finished=finished,
            on_time=sum(p.on_time for p in parts),
            average_days=round(weighted / finished, 1) if finished else None,
        )

    return [*rows, TargetRow(severity="All severities", forward=total("forward"), decide=total("decide"), close=total("close"))]


def _overdue(db: Session, conditions: list) -> Overdue:
    waiting = Complaint.decided_at.is_(None)
    counts = dict(
        db.execute(
            select(waiting, func.count())
            .select_from(Complaint)
            .join(Severity, Severity.id == Complaint.severity_id)
            .where(*conditions, overdue())
            .group_by(waiting)
        ).all()
    )
    deciding, closing = counts.get(True, 0), counts.get(False, 0)
    return Overdue(total=deciding + closing, awaiting_decision=deciding, awaiting_close=closing)


def _options(db: Session) -> FilterOptions:
    def options(model, order) -> list[Option]:
        return [Option(id=i, name=n) for i, n in db.execute(select(model.id, model.name).order_by(order)).all()]

    return FilterOptions(
        areas=options(Area, Area.name),
        categories=options(ComplaintCategory, ComplaintCategory.name),
        severities=options(Severity, Severity.rank),
        mediums=options(ComplaintMedium, ComplaintMedium.name),
    )


def statistics(db: Session, f: StatisticsFilters) -> StatisticsOut:
    conditions = _conditions(f)

    by_status = dict(db.execute(select(Complaint.status, func.count()).where(*conditions).group_by(Complaint.status)).all())
    month = func.to_char(func.timezone(LOCAL_TIMEZONE, Complaint.registered_at), "YYYY-MM")
    by_month = db.execute(select(month, func.count()).where(*conditions).group_by(month).order_by(month)).all()

    return StatisticsOut(
        total=sum(by_status.values()),
        by_status=[CountRow(key=s.value, count=by_status.get(s, 0)) for s in STATUSES],
        by_area=_by(db, Area.name, Area, Area.id == Complaint.area_id, conditions),
        by_category=_by(db, ComplaintCategory.name, ComplaintCategory, ComplaintCategory.id == Complaint.category_id, conditions),
        by_severity=_by(db, Severity.name, Severity, Severity.id == Complaint.severity_id, conditions, order=Severity.rank),
        by_medium=_by(db, ComplaintMedium.name, ComplaintMedium, ComplaintMedium.id == Complaint.medium_id, conditions),
        by_month=[CountRow(key=m, count=n) for m, n in by_month],
        time_targets=_time_targets(db, f, conditions),
        overdue=_overdue(db, conditions),
        options=_options(db),
    )
