"""Figures for the administrator dashboard (UI-AD-01).

Each function is one or a few database queries; build_dashboard puts them together.
All counting is done by the database, and names are masked here, because the
administrator must never receive personal data. needs_attention turns the other
figures into the short list of things the administrator should deal with.
"""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import distinct, exists, func, select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.timezone import LOCAL, LOCAL_TIMEZONE
from app.models import Area, AuthSession, ComplainantAccount, Complaint, Permit, Severity, UsageLog, User, Vehicle
from app.schemas.admin_dashboard import (
    AdminDashboard,
    AreaStatus,
    AttentionItem,
    ComplaintVolume,
    Count,
    MasterData,
    PortalUsers,
    Sessions,
    TimeTarget,
    UsageEvent,
)
from app.schemas.system_health import Backup, FileStorage, ServiceStatus
from app.services import master_data_service, system_health_service
from app.services.l2_case_service import overdue

HOURS_SHOWN = 24
RECENT_EVENTS_SHOWN = 6
COMPLAINT_DAYS = 30
# Where each item of "Needs you" is dealt with, and the usual label of its button.
SYSTEM_HEALTH = "/admin/system-health"
USERS = "/admin/users"
OPEN = {SYSTEM_HEALTH: "Open System health", USERS: "Open Users"}

# Staff roles in the order the dashboard lists them.
ROLE_GROUPS = {
    UserRole.L1: "Level 1 office staff",
    UserRole.L2: "Level 2 area officers",
    UserRole.L3: "Level 3 chairman",
    UserRole.ADMIN: "Administrators",
    UserRole.IMPLEMENTING_STAFF: "Implementing staff",
}
ROLE_NAMES = {
    UserRole.L1: "Level 1",
    UserRole.L2: "Level 2",
    UserRole.L3: "Level 3",
    UserRole.ADMIN: "Administrator",
    UserRole.IMPLEMENTING_STAFF: "Implementing staff",
}
EVENT_LABELS = {"login": "signed in", "logout": "signed out", "login_failed": "failed sign-in"}


def mask_name(name: str) -> str:
    """'Kavindu Perera' becomes 'K***** P*****'. Long words are cut short so the length is not given away."""
    return " ".join(word[0] + "*" * min(len(word) - 1, 5) for word in name.split())


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def sessions_summary(db: Session, now: datetime) -> Sessions:
    # A session counts as live until it is revoked or runs out of time.
    staff, portal = db.execute(
        select(func.count(distinct(AuthSession.user_id)), func.count(distinct(AuthSession.account_id))).where(
            AuthSession.revoked_at.is_(None),
            AuthSession.idle_expires_at > now,
            AuthSession.absolute_expires_at > now,
        )
    ).one()

    events = dict(
        db.execute(
            select(UsageLog.event_type, func.count())
            .where(UsageLog.occurred_at >= now - timedelta(hours=24), UsageLog.event_type.in_(["login", "login_failed"]))
            .group_by(UsageLog.event_type)
        ).all()
    )

    locked = sum(_count(db, model, model.locked_until > now) for model in (User, ComplainantAccount))

    return Sessions(
        signed_in_now=staff + portal,
        sign_ins_today=events.get("login", 0),
        failed_today=events.get("login_failed", 0),
        locked_accounts=locked,
    )


def staff_by_role(db: Session) -> list[Count]:
    counts = dict(db.execute(select(User.role, func.count()).where(User.is_active).group_by(User.role)).all())
    return [Count(label=label, count=counts.get(role, 0)) for role, label in ROLE_GROUPS.items()]


def sign_ins_per_hour(db: Session, now: datetime) -> tuple[list[int], int]:
    """Sign-ins in each of the last 24 local hours (oldest first), and the current local hour."""
    now_local = now.astimezone(LOCAL)
    first_hour = now_local.replace(minute=0, second=0, microsecond=0) - timedelta(hours=HOURS_SHOWN - 1)

    hour = func.date_trunc("hour", func.timezone(LOCAL_TIMEZONE, UsageLog.occurred_at))
    rows = db.execute(
        select(hour, func.count())
        .where(UsageLog.event_type == "login", UsageLog.occurred_at >= first_hour)
        .group_by(hour)
    ).all()
    by_hour = dict(rows)

    start = first_hour.replace(tzinfo=None)  # the database returns local times without a zone
    return [by_hour.get(start + timedelta(hours=i), 0) for i in range(HOURS_SHOWN)], now_local.hour


def recent_usage(db: Session) -> list[UsageEvent]:
    rows = db.execute(
        select(
            UsageLog.event_type,
            UsageLog.occurred_at,
            UsageLog.user_id,
            UsageLog.account_id,
            User.full_name,
            User.role,
            ComplainantAccount.display_name,
        )
        .outerjoin(User, User.id == UsageLog.user_id)
        .outerjoin(ComplainantAccount, ComplainantAccount.id == UsageLog.account_id)
        .where(UsageLog.event_type.in_(EVENT_LABELS))
        .order_by(UsageLog.id.desc())
        .limit(RECENT_EVENTS_SHOWN)
    ).all()

    events = []
    for event_type, at, user_id, account_id, staff_name, staff_role, portal_name in rows:
        if user_id:
            who, role = mask_name(staff_name), ROLE_NAMES[staff_role]
        elif account_id:
            who, role = mask_name(portal_name or "Portal user"), "Portal"
        else:  # a failed sign-in with a name that matches no account
            who, role = "Unknown login", "No account"
        events.append(
            UsageEvent(time=at.astimezone(LOCAL).strftime("%H:%M"), who=who, role=role, event=EVENT_LABELS[event_type])
        )
    return events


def area_coverage(db: Session) -> list[AreaStatus]:
    vehicles = (
        select(func.count())
        .where(Vehicle.registered_area_id == Area.id, Vehicle.is_active)
        .scalar_subquery()
    )
    officer = exists().where(User.area_id == Area.id, User.role == UserRole.L2, User.is_active)
    rows = db.execute(select(Area.name, vehicles, officer).where(Area.is_active).order_by(Area.name)).all()
    return [AreaStatus(name=name, vehicles=count, has_officer=has) for name, count, has in rows]


def master_data_counts(db: Session) -> MasterData:
    active = {entity.key: entity.active for entity in master_data_service.counts(db)}
    has_permit = exists().where(Permit.vehicle_id == Vehicle.id, Permit.is_active)
    return MasterData(
        people=active["people"],
        vehicles=active["vehicles"],
        permits=active["permits"],
        routes_and_stands=active["routes"],
        categories=active["categories"],
        vehicles_without_permit=_count(db, Vehicle, Vehicle.is_active, ~has_permit),
    )


def complaint_volume(db: Session, now: datetime) -> ComplaintVolume:
    first_day = now.astimezone(LOCAL).date() - timedelta(days=COMPLAINT_DAYS - 1)
    recent = Complaint.registered_at >= datetime.combine(first_day, time(), LOCAL)
    count = func.count(Complaint.id)

    day = func.date(func.timezone(LOCAL_TIMEZONE, Complaint.registered_at))
    per_day = dict(db.execute(select(day, count).where(recent).group_by(day)).all())
    by_area = db.execute(
        select(Area.name, count)
        .join(Area, Area.id == Complaint.area_id)
        .where(recent)
        .group_by(Area.name)
        .order_by(Area.name)
    ).all()
    by_status = db.execute(
        select(Complaint.status, count).where(recent).group_by(Complaint.status).order_by(count.desc())
    ).all()
    overdue_now = db.scalar(
        select(func.count()).select_from(Complaint).join(Severity, Severity.id == Complaint.severity_id).where(overdue())
    )

    return ComplaintVolume(
        per_day=[per_day.get(first_day + timedelta(days=i), 0) for i in range(COMPLAINT_DAYS)],
        by_area=[Count(label=name, count=n) for name, n in by_area],
        by_status=[Count(label=status.value, count=n) for status, n in by_status],
        overdue=overdue_now or 0,
    )


def time_targets(db: Session) -> list[TimeTarget]:
    severities = db.scalars(select(Severity).where(Severity.is_active).order_by(Severity.rank))
    return [
        TimeTarget(severity=s.name, forward_days=s.forward_days, decide_days=s.decide_days, close_days=s.close_days)
        for s in severities
    ]


def needs_attention(
    *,
    areas: list[AreaStatus],
    services: list[ServiceStatus],
    storage: FileStorage,
    backup: Backup | None,
    locked_staff: int,
) -> list[AttentionItem]:
    """What the administrator should deal with, most urgent first."""
    items: list[AttentionItem] = []

    def add(tone: str, title: str, detail: str, href: str, action: str | None = None) -> None:
        items.append(AttentionItem(tone=tone, title=title, detail=detail, href=href, action=action or OPEN[href]))

    for area in areas:
        if not area.has_officer:
            add("crit", f"{area.name} has no active Level 2 officer", "Complaints for this area cannot be forwarded.",
                USERS, "Assign officer")

    for service in services:
        if service.status == "down":
            add("crit", f"The {service.name} is not responding", "See System health.", SYSTEM_HEALTH)
        elif service.status == "slow":
            add("warn", f"The {service.name} is slow", f"Its last answer took {service.latency_ms} ms.", SYSTEM_HEALTH)

    if backup is None:
        add("warn", "No backup has been made yet", "Schedule the daily backup script.", SYSTEM_HEALTH)
    elif not backup.succeeded:
        add("crit", "The last backup failed", backup.error or "See System health.", SYSTEM_HEALTH)
    elif backup.stale:
        add("warn", "The daily backup did not run", "The last one is more than a day old.", SYSTEM_HEALTH)

    if storage.low:
        free = round(100 * storage.free_bytes / storage.total_bytes)
        add("warn", "File storage is almost full", f"{free}% of the disk is free.", SYSTEM_HEALTH)

    if locked_staff:
        accounts = "account is" if locked_staff == 1 else "accounts are"
        add("info", f"{locked_staff} staff {accounts} locked", "Unlock them under Users.", USERS)

    urgency = {"crit": 0, "warn": 1, "info": 2}
    return sorted(items, key=lambda item: urgency[item.tone])  # sorted() keeps the order within a tone


def build_dashboard(db: Session) -> AdminDashboard:
    now = datetime.now(UTC)
    per_hour, current_hour = sign_ins_per_hour(db, now)
    areas = area_coverage(db)
    services = system_health_service.service_statuses(db, now)
    storage = system_health_service.file_storage(db)
    backup = system_health_service.last_backup(db, now)
    return AdminDashboard(
        sessions=sessions_summary(db, now),
        staff_by_role=staff_by_role(db),
        portal_users=PortalUsers(
            total=_count(db, ComplainantAccount, ComplainantAccount.is_active, ComplainantAccount.verified_at.is_not(None)),
            unverified=_count(db, ComplainantAccount, ComplainantAccount.is_active, ComplainantAccount.verified_at.is_(None)),
        ),
        deactivated_users=sum(_count(db, model, model.is_active.is_(False)) for model in (User, ComplainantAccount)),
        sign_ins_per_hour=per_hour,
        current_hour=current_hour,
        recent_usage=recent_usage(db),
        services=services,
        api_response_ms=system_health_service.api_response_series(db, now),
        file_storage=storage,
        last_backup=backup,
        attention=needs_attention(
            areas=areas,
            services=services,
            storage=storage,
            backup=backup,
            locked_staff=_count(db, User, User.is_active, User.locked_until > now),
        ),
        areas=areas,
        master_data=master_data_counts(db),
        complaints=complaint_volume(db, now),
        time_targets=time_targets(db),
    )
