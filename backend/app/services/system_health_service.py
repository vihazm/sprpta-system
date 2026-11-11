"""Figures for the administrator's System health page (UI-AD-07).

Everything is read from the readings that health_check_service saves, plus a few
live numbers from the database server. Each function is one or two queries.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, literal_column, select, text
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.core.timezone import LOCAL, LOCAL_TIMEZONE
from app.models import HealthCheck, HealthEvent, UsageLog, User
from app.schemas.system_health import (
    DatabaseStats,
    HealthEventOut,
    Outage,
    ServiceStatus,
    SystemHealth,
    Uptime,
)
from app.services.health_check_service import INTERVAL_SECONDS, SERVICE_NAMES, STARTED_AT

UPTIME_DAYS = 30
SERIES_HOURS = 24
EVENTS_SHOWN = 8
FAILED_SIGN_INS_TO_REPORT = 5
# A reading older than this is not shown as current: the checks may have stopped.
STALE_AFTER = timedelta(seconds=INTERVAL_SECONDS * 3)

EVENT_TITLES = {
    "ok": "{name} is back to normal",
    "slow": "{name} slowed down",
    "down": "{name} stopped responding",
    "started": "{name} started",
}
EVENT_TONES = {"ok": "ok", "slow": "warn", "down": "crit", "started": "info"}


def _latest_readings(db: Session) -> dict[str, HealthCheck]:
    rows = db.scalars(
        select(HealthCheck)
        .ext(distinct_on(HealthCheck.service))
        .order_by(HealthCheck.service, HealthCheck.checked_at.desc())
    )
    return {row.service: row for row in rows}


def service_statuses(db: Session, now: datetime) -> list[ServiceStatus]:
    latest = _latest_readings(db)
    statuses = []
    for key, name in SERVICE_NAMES.items():
        reading = latest.get(key)
        if reading is None or now - reading.checked_at > STALE_AFTER:
            statuses.append(ServiceStatus(key=key, name=name, status="unknown", latency_ms=None))
        else:
            statuses.append(ServiceStatus(key=key, name=name, status=reading.status, latency_ms=reading.latency_ms))
    return statuses


def _series(db: Session, now: datetime, service: str | None = None) -> dict[str, list[int]]:
    """Average response time in 15 minute steps over the last 24 hours, oldest first."""
    step = func.date_bin(
        literal_column("interval '15 minutes'"), HealthCheck.checked_at, literal_column("timestamptz '2001-01-01 00:00:00+00'")
    )
    query = (
        select(HealthCheck.service, func.round(func.avg(HealthCheck.latency_ms)))
        .where(HealthCheck.checked_at >= now - timedelta(hours=SERIES_HOURS), HealthCheck.latency_ms.is_not(None))
        .group_by(HealthCheck.service, step)
        .order_by(step)
    )
    if service:
        query = query.where(HealthCheck.service == service)
    series: dict[str, list[int]] = {key: [] for key in SERVICE_NAMES}
    for key, average in db.execute(query):
        series[key].append(int(average))
    return series


def api_response_series(db: Session, now: datetime) -> list[int]:
    return _series(db, now, "api")["api"]


def _uptime(db: Session, now: datetime) -> Uptime:
    local_day = func.date(func.timezone(LOCAL_TIMEZONE, HealthCheck.checked_at))
    down = func.count().filter(HealthCheck.status == "down")
    rows = db.execute(
        select(local_day, func.count(), down)
        .where(HealthCheck.checked_at >= now - timedelta(days=UPTIME_DAYS + 1))
        .group_by(local_day)
    ).all()
    by_day = {day: (total, downs) for day, total, downs in rows}

    today = now.astimezone(LOCAL).date()
    days = []
    for back in range(UPTIME_DAYS - 1, -1, -1):
        total, downs = by_day.get(today - timedelta(days=back), (0, 0))
        days.append("unknown" if total == 0 else "down" if downs else "up")

    total = sum(t for t, _ in by_day.values())
    downs = sum(d for _, d in by_day.values())
    return Uptime(
        percent=round(100 * (total - downs) / total, 2) if total else None,
        days=days,
        tracking_since=db.scalar(select(func.min(HealthCheck.checked_at))),
        last_outage=_last_outage(db, now),
    )


def _last_outage(db: Session, now: datetime) -> Outage | None:
    outage = db.scalar(
        select(HealthEvent).where(HealthEvent.status == "down").order_by(HealthEvent.occurred_at.desc()).limit(1)
    )
    if outage is None:
        return None
    recovered = db.scalar(
        select(func.min(HealthEvent.occurred_at)).where(
            HealthEvent.service == outage.service, HealthEvent.status == "ok", HealthEvent.occurred_at > outage.occurred_at
        )
    )
    return Outage(
        service_name=SERVICE_NAMES[outage.service],
        started_at=outage.occurred_at,
        minutes=max(1, round((recovered - outage.occurred_at).total_seconds() / 60)) if recovered else None,
        reason=outage.detail,
    )


def _database_stats(db: Session) -> DatabaseStats:
    connections, max_connections, size, started = db.execute(
        text(
            "select (select count(*) from pg_stat_activity where datname = current_database()),"
            " current_setting('max_connections')::int,"
            " pg_database_size(current_database()),"
            " pg_postmaster_start_time()"
        )
    ).one()
    return DatabaseStats(connections=connections, max_connections=max_connections, size_bytes=size, started_at=started)


def _events(db: Session, now: datetime) -> list[HealthEventOut]:
    events = [
        HealthEventOut(
            title=EVENT_TITLES[e.status].format(name=SERVICE_NAMES[e.service]),
            detail=e.detail,
            occurred_at=e.occurred_at,
            tone=EVENT_TONES[e.status],
        )
        for e in db.scalars(select(HealthEvent).order_by(HealthEvent.occurred_at.desc()).limit(EVENTS_SHOWN))
    ]

    # Things happening to accounts right now, from the sign-in records.
    failed = db.scalar(
        select(func.count())
        .select_from(UsageLog)
        .where(UsageLog.event_type == "login_failed", UsageLog.occurred_at >= now - timedelta(hours=1))
    )
    if failed >= FAILED_SIGN_INS_TO_REPORT:
        events.append(
            HealthEventOut(title=f"{failed} failed sign-ins in the last hour", detail=None, occurred_at=now, tone="warn")
        )
    locked = db.scalar(select(func.count()).select_from(User).where(User.is_active, User.locked_until > now))
    if locked:
        plural = "account is" if locked == 1 else "accounts are"
        events.append(HealthEventOut(title=f"{locked} {plural} locked", detail=None, occurred_at=now, tone="warn"))

    return sorted(events, key=lambda e: e.occurred_at, reverse=True)[:EVENTS_SHOWN]


def build_system_health(db: Session) -> SystemHealth:
    now = datetime.now(UTC)
    return SystemHealth(
        checked_at=db.scalar(select(func.max(HealthCheck.checked_at))),
        services=service_statuses(db, now),
        series=_series(db, now),
        uptime=_uptime(db, now),
        database=_database_stats(db),
        api_started_at=STARTED_AT,
        events=_events(db, now),
    )
