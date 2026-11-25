"""The Level 1 dashboard (UC-L1-12): every number comes from the complaints and audit_log tables.

Two scopes, on purpose:
- "Your day so far" and the weekly and monthly counts are the signed-in officer's own work, counted in Sri
  Lankan time: Entered = complaints they created, Forwarded = complaints they forwarded (audit_log), Still open =
  of today's entries, those still a draft or incomplete.
- "Needs attention" is the shared Level 1 queue (drafts, incomplete cases, portal submissions, possible
  duplicates), because any Level 1 officer can pick one up and finish it.
"""

from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL
from app.models import AuditLog, Complaint, ComplaintTargetType
from app.schemas.l1_dashboard import ByTarget, DashboardOut, DaySummary, PortalCase, Queues, WaitingCase
from app.services.auth_service import Principal
from app.services.complaint_list_service import EDITABLE, undecided_duplicate

WAITING_LIMIT = 6
PORTAL_LIMIT = 5


def _minutes_since(moment: datetime, now: datetime) -> int:
    return max(0, int((now - moment).total_seconds() // 60))


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(Complaint).where(*conditions)) or 0


def _by_target(db: Session, officer: Principal) -> ByTarget:
    """This officer's own complaints (every status) counted by who they are against."""
    found = dict(
        db.execute(
            select(ComplaintTargetType.code, func.count(Complaint.id))
            .join(Complaint, Complaint.target_type_id == ComplaintTargetType.id)
            .where(Complaint.entered_by_user_id == officer.id)
            .group_by(ComplaintTargetType.code)
        ).all()
    )
    return ByTarget(
        driver=found.get("driver", 0),
        conductor=found.get("conductor", 0),
        owner=found.get("owner", 0),
        bus_service=found.get("bus_service", 0),
        other=found.get("other", 0),
        unclassified=_count(db, Complaint.entered_by_user_id == officer.id, Complaint.target_type_id.is_(None)),
    )


def dashboard(db: Session, officer: Principal) -> DashboardOut:
    now = datetime.now(LOCAL)
    today = datetime.combine(now.date(), time.min, LOCAL)
    monday = today - timedelta(days=today.weekday())
    first = today.replace(day=1)
    mine = Complaint.entered_by_user_id == officer.id

    forwarded_today = (
        db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "complaint.forward",
                AuditLog.actor_user_id == officer.id,
                AuditLog.occurred_at >= today,
            )
        )
        or 0
    )

    waiting = db.execute(
        select(Complaint, undecided_duplicate())
        .where(Complaint.status.in_(EDITABLE))
        .order_by(Complaint.created_at, Complaint.id)  # the longest waiting first
        .limit(WAITING_LIMIT)
    ).all()
    portal = db.scalars(
        select(Complaint)
        .where(Complaint.status == ComplaintStatus.SUBMITTED, Complaint.withdrawn_at.is_(None))
        .order_by(Complaint.created_at, Complaint.id)
        .limit(PORTAL_LIMIT)
    ).all()

    return DashboardOut(
        day=DaySummary(
            entered=_count(db, mine, Complaint.created_at >= today),
            forwarded=forwarded_today,
            still_open=_count(db, mine, Complaint.created_at >= today, Complaint.status.in_(EDITABLE)),
        ),
        week_entered=_count(db, mine, Complaint.created_at >= monday),
        month_entered=_count(db, mine, Complaint.created_at >= first),
        queues=Queues(
            portal=_count(db, Complaint.status == ComplaintStatus.SUBMITTED, Complaint.withdrawn_at.is_(None)),
            drafts=_count(db, Complaint.status == ComplaintStatus.DRAFT),
            incomplete=_count(db, Complaint.status == ComplaintStatus.INCOMPLETE),
            duplicates=_count(db, Complaint.status.in_(EDITABLE), undecided_duplicate()),
        ),
        by_target=_by_target(db, officer),
        waiting=[
            WaitingCase(
                id=c.id,
                reference_number=c.reference_number,
                subject=c.subject,
                status=c.status,
                possible_duplicate=duplicate,
                age_minutes=_minutes_since(c.created_at, now),
            )
            for c, duplicate in waiting
        ],
        portal=[
            PortalCase(
                id=c.id, subject=c.subject, complainant=c.complainant_name, age_minutes=_minutes_since(c.created_at, now)
            )
            for c in portal
        ],
    )
