"""The lower cards of the Level 1 dashboard: sources, area totals, transport and severity, recently forwarded."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SeverityName = Literal["critical", "high", "medium", "low"]


class SourceRow(BaseModel):
    label: str  # the medium the complaint reached SPRPTA by, or "Not recorded"
    count: int


class BusiestMedium(BaseModel):
    medium: str | None  # none while nothing was entered this week
    count: int
    total: int  # all the officer's complaints this week


class AreaCount(BaseModel):
    name: str
    count: int  # this officer's complaints forwarded this month to this area's officer
    has_officer: bool  # an active Level 2 officer is assigned to the area


class TransportCounts(BaseModel):
    bus: int
    trishaw: int
    unknown: int  # no vehicle on record yet


class SeverityCount(BaseModel):
    severity: SeverityName
    count: int


class ForwardedRow(BaseModel):
    id: int
    reference_number: str | None
    title: str | None
    severity: SeverityName | None
    area_name: str | None
    forwarded_at: datetime
    has_contact: bool  # a mobile number or an email is on record, so a registration message is due
    message_sent: bool  # the registration message went out


class OverviewOut(BaseModel):
    """Every figure is this officer's own work, counted in Sri Lankan time."""

    month_total: int
    sources: list[SourceRow]  # this month, by medium
    busiest_week: BusiestMedium
    areas: list[AreaCount]  # forwarded this month
    forwarded_total: int
    transport: TransportCounts  # this month
    severity: list[SeverityCount]  # this month, always the four levels
    forwarded: list[ForwardedRow]  # the latest forwarded
