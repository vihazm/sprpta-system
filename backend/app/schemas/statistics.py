"""Complaint statistics (UI-AD-11, the same measures as UI-L3-02). Counts and days only: nothing personal."""

from datetime import date

from pydantic import BaseModel


class StatisticsFilters(BaseModel):
    date_from: date | None = None  # registration date, inclusive
    date_to: date | None = None
    area_id: int | None = None
    category_id: int | None = None
    severity_id: int | None = None
    medium_id: int | None = None


class Option(BaseModel):
    id: int
    name: str


class FilterOptions(BaseModel):
    areas: list[Option]
    categories: list[Option]
    severities: list[Option]
    mediums: list[Option]


class CountRow(BaseModel):
    key: str  # a status, a name, or "yyyy-mm" for a month
    count: int


class Stage(BaseModel):
    """One time target: of the complaints that finished this stage, how many did it in time."""

    target_days: int | None  # None on the row that adds up all severities
    finished: int
    on_time: int
    average_days: float | None


class TargetRow(BaseModel):
    severity: str
    forward: Stage
    decide: Stage
    close: Stage


class Overdue(BaseModel):
    total: int
    awaiting_decision: int  # past decide-by
    awaiting_close: int  # decided, past close-by


class StatisticsOut(BaseModel):
    total: int
    by_status: list[CountRow]
    by_area: list[CountRow]
    by_category: list[CountRow]
    by_severity: list[CountRow]
    by_medium: list[CountRow]
    by_month: list[CountRow]
    time_targets: list[TargetRow]  # one row per severity, then "All severities"
    overdue: Overdue
    options: FilterOptions
