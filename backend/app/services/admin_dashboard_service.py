"""Figures for the administrator dashboard (UI-AD-01).

Each function is one database query; build_dashboard puts them together.
All counting is done by the database, and names are masked here, because the
administrator must never receive personal data.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.models import AuthSession, ComplainantAccount, UsageLog, User
from app.schemas.admin_dashboard import (
    AdminDashboard,
    Count,
    PortalUsers,
    Sessions,
    UsageEvent,
)

LOCAL_TIMEZONE = "Asia/Colombo"
LOCAL = ZoneInfo(LOCAL_TIMEZONE)
HOURS_SHOWN = 24
RECENT_EVENTS_SHOWN = 6

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


def build_dashboard(db: Session) -> AdminDashboard:
    now = datetime.now(UTC)
    per_hour, current_hour = sign_ins_per_hour(db, now)
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
    )
