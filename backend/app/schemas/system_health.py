"""Response shapes of the administrator's System health page (UI-AD-07).

The web app, the API and the database are timed by the health checks. File storage and the
last backup are read when the page is asked for. The AI service and messaging have no source yet.
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


class FileStorage(BaseModel):
    total_bytes: int  # the disk the evidence folder is on
    free_bytes: int
    low: bool  # less than a tenth of the disk is free
    evidence_files: int
    evidence_bytes: int


class Backup(BaseModel):
    """The last run of the backup script (F-66)."""

    finished_at: datetime
    succeeded: bool
    size_bytes: int | None  # the database dump and the evidence files together
    error: str | None
    stale: bool  # more than a day old, so the daily run has been missed


class SystemHealth(BaseModel):
    checked_at: datetime | None  # when the newest reading was taken
    services: list[ServiceStatus]
    series: dict[str, list[int]]  # average response time per service, 15 minute steps over 24 hours
    uptime: Uptime
    database: DatabaseStats
    api_started_at: datetime
    events: list[HealthEventOut]
    file_storage: FileStorage
    last_backup: Backup | None  # None until the backup script has run once
