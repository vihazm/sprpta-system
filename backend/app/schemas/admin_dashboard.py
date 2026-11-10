"""Response shapes of the administrator dashboard (UI-AD-01).

Only the figures the database can answer today are here; the frontend keeps
sample data for the rest until those modules exist.
"""

from pydantic import BaseModel


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


class AdminDashboard(BaseModel):
    sessions: Sessions
    staff_by_role: list[Count]
    portal_users: PortalUsers
    deactivated_users: int
    sign_ins_per_hour: list[int]  # last 24 hours, oldest first, the last one is the current hour
    current_hour: int  # 0 to 23, local time
    recent_usage: list[UsageEvent]
