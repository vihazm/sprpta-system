"""Response shapes of the administrator dashboard (UI-AD-01).

Only the figures the system can answer today are here; the frontend keeps sample
data for the policy library until that module exists.
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.system_health import Backup, FileStorage, ServiceStatus


class Count(BaseModel):
    label: str
    count: int


class Sessions(BaseModel):
    signed_in_now: int
    sign_ins_today: int  # the last 24 hours
    failed_today: int
    locked_accounts: int


class PortalUsers(BaseModel):
    total: int
    unverified: int


class UsageEvent(BaseModel):
    time: str  # local time, HH:MM
    who: str  # masked: the administrator never sees personal data
    role: str
    event: str  # "signed in", "signed out" or "failed sign-in"


class AttentionItem(BaseModel):
    title: str
    detail: str
    tone: Literal["crit", "warn", "info"]
    href: str  # the page where it is dealt with
    action: str  # the label of the button that opens it


class AreaStatus(BaseModel):
    name: str
    vehicles: int  # active vehicles registered to the area
    has_officer: bool  # an active Level 2 officer


class MasterData(BaseModel):
    """Active records of each list."""

    people: int
    vehicles: int
    permits: int
    routes_and_stands: int
    categories: int
    vehicles_without_permit: int


class ComplaintVolume(BaseModel):
    """Registered complaints over the last 30 days. Counts only, so nothing personal."""

    per_day: list[int]  # oldest first, the last one is today
    by_area: list[Count]
    by_status: list[Count]  # the label is the status key, for example "under_review"
    overdue: int  # open cases past a time target now, of any age


class Messages(BaseModel):
    """Messages to complainants in the last 24 hours, counted from the message log."""

    sent: int
    failed: int
    by_type: list[Count]  # every kind of message, in the order of the templates screen


class TimeTarget(BaseModel):
    severity: str
    forward_days: int
    decide_days: int
    close_days: int


class AdminDashboard(BaseModel):
    sessions: Sessions
    staff_by_role: list[Count]
    portal_users: PortalUsers
    deactivated_users: int
    sign_ins_per_hour: list[int]  # last 24 hours, oldest first, the last one is the current hour
    current_hour: int  # 0 to 23, local time
    recent_usage: list[UsageEvent]
    services: list[ServiceStatus]  # the ones the backend can check itself
    api_response_ms: list[int]  # last 24 hours, oldest first
    file_storage: FileStorage
    last_backup: Backup | None  # None until the backup script has run once
    attention: list[AttentionItem]  # most urgent first
    areas: list[AreaStatus]
    master_data: MasterData
    messages: Messages
    complaints: ComplaintVolume
    time_targets: list[TimeTarget]
