"""Request and response shapes of the Level 2 dashboard and case screens (UC-L2-01, 02, 04, 05, 07)."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import (
    ComplaintStatus,
    DecisionAction,
    DecisionOutcome,
    DuplicateLinkType,
    RecommendationStatus,
    RecommendationType,
)
from app.schemas.l1_complaints import Text

# A status the officer can filter the list by, or "overdue" (a flag, never a status).
CaseFilter = Literal[
    "forwarded", "under_review", "awaiting_implementation", "done_awaiting_approval", "escalated", "closed", "overdue"
]
SeverityFilter = Literal["critical", "high", "medium", "low"]
# "urgent" puts overdue cases first, then the nearest time target; "newest" is by forwarding date.
CaseSort = Literal["urgent", "newest"]
# Which time target applies now: decide-by while the case waits for a decision, close-by after it.
DueKind = Literal["decide", "close"]


class CaseRow(BaseModel):
    id: int
    reference_number: str
    status: ComplaintStatus
    subject: str | None
    vehicle_number: str | None
    severity: str  # the severity's name in lower case, for example "critical"
    forwarded_at: datetime | None
    due_kind: DueKind | None
    due_at: datetime | None
    overdue: bool


class CasePage(BaseModel):
    items: list[CaseRow]
    total: int
    page: int
    page_size: int
    counts: dict[str, int]  # per status, plus "all" and "overdue", matching the search and the severity


class TimeTarget(BaseModel):
    severity: str
    forward_days: int
    decide_days: int
    close_days: int


class RecommendationRow(BaseModel):
    id: int
    recommendation_type: RecommendationType
    status: RecommendationStatus
    title: str
    received_date: date | None
    created_at: datetime


class DashboardOut(BaseModel):
    counts: dict[str, int]  # the area's cases per status, plus "all" and "overdue"
    arrived_today: int  # forwarded to the area today
    decided_today: int  # decisions this officer recorded today
    closed_this_month: int
    urgent: int  # critical cases still waiting for a decision
    next_case_id: int | None  # the most urgent case waiting for a decision
    overdue: list[CaseRow]
    average_decide_days: float | None  # this month, from registration to decision
    targets: list[TimeTarget]
    recommendations: list[RecommendationRow]


# ---------------------------------------------------------------- one case


class AttachmentInfo(BaseModel):
    id: int
    file_name: str
    mime_type: str
    size_bytes: int


class EarlierCase(BaseModel):
    id: int
    reference_number: str
    subject: str | None
    status: ComplaintStatus
    registered_at: datetime | None
    action: DecisionAction | None
    outcome: DecisionOutcome | None


class DuplicateDecision(BaseModel):
    reference_number: str | None
    link_type: DuplicateLinkType


class HistoryEntry(BaseModel):
    occurred_at: datetime
    actor_name: str | None
    actor_role: str
    action: str
    from_status: ComplaintStatus | None
    to_status: ComplaintStatus | None
    reason: str | None


class DecisionOut(BaseModel):
    action: DecisionAction
    outcome: DecisionOutcome
    reasoning: str
    decided_by: str
    decided_at: datetime


class SolutionDocumentOut(BaseModel):
    summary_text: str
    verdict_text: str
    solution_details: str | None
    generated_by: str
    generated_at: datetime


class EscalationOut(BaseModel):
    reason: str
    escalated_by: str
    escalated_at: datetime


class CaseDetail(BaseModel):
    id: int
    reference_number: str
    status: ComplaintStatus
    severity: str
    due_kind: DueKind | None
    due_at: datetime | None
    overdue: bool
    subject: str | None
    description: str | None
    category: str | None
    target: str | None  # who the complaint is against
    accused: str | None  # the person named, as a record or as written
    medium: str | None
    is_anonymous: bool
    complainant: str | None
    has_contact: bool  # Level 2 sees only whether a phone or email was recorded, not the contact itself
    complainant_type: str | None  # passenger, driver, conductor, owner or other
    complaint_date: date | None
    incident_time: time | None
    incident_location: str | None
    bus_verification: str | None  # what Level 1's check of the bus against the daily records found
    driver_on_duty: str | None  # from the verified daily record, when Level 1 selected a trip
    conductor_on_duty: str | None
    vehicle_number: str | None
    vehicle_type: str | None
    permit_number: str | None
    owner: str | None
    route_stand: str | None
    area: str | None
    registered_at: datetime | None
    forwarded_at: datetime | None
    forwarded_by: str | None
    attachments: list[AttachmentInfo]
    earlier: list[EarlierCase]
    duplicates: list[DuplicateDecision]
    history: list[HistoryEntry]
    decision: DecisionOut | None
    solution_document: SolutionDocumentOut | None
    escalation: EscalationOut | None


# ---------------------------------------------------------------- what the officer sends


class DecisionBody(BaseModel):
    action: DecisionAction
    outcome: DecisionOutcome
    reasoning: Text = Field(min_length=1, max_length=5000, pattern=r"\S")


class SolutionDocumentBody(BaseModel):
    summary: Text = Field(min_length=1, max_length=2000, pattern=r"\S")
    solution_details: Text = Field(min_length=1, max_length=5000, pattern=r"\S")


class EscalateBody(BaseModel):
    reason: Text = Field(min_length=1, max_length=1000, pattern=r"\S")
