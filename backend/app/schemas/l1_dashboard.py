"""Response shapes of the Level 1 dashboard and the complaint lists behind its cards (UC-L1-12)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.core.enums import ComplaintStatus

# The filters the Complaints page offers. "forwarded" is every case that has left Level 1;
# "duplicates" is the drafts and incomplete cases with an earlier case on the same bus still to be decided.
ListFilter = Literal["draft", "incomplete", "submitted", "forwarded", "rejected", "duplicates"]
# Who a complaint is against, as the Complaints page filters by it.
TargetFilter = Literal["driver", "conductor", "owner", "bus_service", "other", "unclassified"]
# "mine" is what this officer registered; "all" is the whole Level 1 queue (the dashboard cards open that).
Scope = Literal["mine", "all"]


class DaySummary(BaseModel):
    """The signed-in officer's own day, in Sri Lankan time."""

    entered: int  # complaints this officer created today
    forwarded: int  # complaints this officer forwarded today (whenever they were entered)
    still_open: int  # of those entered today, how many are still a draft or incomplete


class Queues(BaseModel):
    """What is waiting for Level 1. Shared by all Level 1 staff, since any of them can finish a draft."""

    portal: int  # submitted through the portal, waiting for the first check
    drafts: int
    incomplete: int
    duplicates: int  # drafts and incomplete cases with an earlier case on the same bus still to be decided


class WaitingCase(BaseModel):
    id: int
    reference_number: str | None  # a draft has none yet
    subject: str | None
    status: ComplaintStatus
    possible_duplicate: bool
    age_minutes: int  # since it was entered


class PortalCase(BaseModel):
    id: int
    subject: str | None
    complainant: str | None
    age_minutes: int


class ByTarget(BaseModel):
    """This officer's complaints counted by who they are against."""

    driver: int
    conductor: int
    owner: int
    bus_service: int
    other: int
    unclassified: int  # not yet classified: drafts started without a target


class DashboardOut(BaseModel):
    day: DaySummary
    week_entered: int  # by this officer since Monday
    month_entered: int  # by this officer since the 1st
    queues: Queues
    by_target: ByTarget
    waiting: list[WaitingCase]  # the oldest drafts and incomplete cases first
    portal: list[PortalCase]


class ComplaintRow(BaseModel):
    id: int
    reference_number: str | None
    status: ComplaintStatus
    subject: str | None
    vehicle_number: str | None
    target_code: str | None  # who the complaint is against
    target_name: str | None
    accused_name: str | None  # the person named, as a record or as written; empty when nobody is identified
    accused_status: str
    category_name: str | None  # the issue type
    complainant: str | None  # empty for an anonymous complaint
    area_name: str | None
    severity_name: str | None
    complaint_date: date | None
    updated_at: datetime
    editable: bool  # a draft or an incomplete case can be opened and finished
    possible_duplicate: bool
    bus_verification: str | None = None
    synthetic: bool = False  # simulated development data


class ComplaintPage(BaseModel):
    items: list[ComplaintRow]
    total: int  # matching the filter and the search
    page: int
    page_size: int
    counts: dict[str, int]  # per status filter, plus "all", matching the search and the target
    target_counts: dict[str, int]  # per target, plus "all", matching the search and the status


class ReferenceHit(BaseModel):
    id: int
    reference_number: str
    status: ComplaintStatus
    editable: bool
    subject: str | None
    area_name: str | None
    forwarded_to: str | None  # the Level 2 officer, once forwarded
    forwarded_at: datetime | None
