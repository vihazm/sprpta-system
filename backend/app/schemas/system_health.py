"""Response shapes of the administrator's System health page (UI-AD-07).

Only the services the backend can check itself are here: the web app, the API and the
database. The rest (files, AI, messages, backups) have no source yet.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# "unknown" means there is no recent reading, for example right after the first start.
Status = Literal["ok", "slow", "down", "unknown"]


class ServiceStatus(BaseModel):
    key: str  # "web", "api" or "database"
    name: str
    status: Status
    latency_ms: int | None


class DatabaseStats(BaseModel):
    connections: int
    max_connections: int
    size_bytes: int
    started_at: datetime


class Outage(BaseModel):
    service_name: str
    started_at: datetime
    minutes: int | None  # None while it is still going on
    reason: str | None


class Uptime(BaseModel):
    percent: float | None  # None until the first reading
    days: list[Literal["up", "down", "unknown"]]  # the last 30 days, oldest first
    tracking_since: datetime | None
    last_outage: Outage | None


class HealthEventOut(BaseModel):
    title: str
    detail: str | None
    occurred_at: datetime
    tone: Literal["ok", "warn", "crit", "info"]


class SystemHealth(BaseModel):
    checked_at: datetime | None  # when the newest reading was taken
    services: list[ServiceStatus]
    series: dict[str, list[int]]  # average response time per service, 15 minute steps over 24 hours
    uptime: Uptime
    database: DatabaseStats
    api_started_at: datetime
    events: list[HealthEventOut]
