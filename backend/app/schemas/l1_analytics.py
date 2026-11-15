"""Dashboard analytics over the signed-in Level 1 officer's own complaints."""

from pydantic import BaseModel


class CountRow(BaseModel):
    id: int | None
    name: str
    count: int


class MonthRow(BaseModel):
    month: str  # yyyy-mm, or "unknown" for a complaint with no date yet
    count: int


class AnalyticsOut(BaseModel):
    total: int
    by_category: list[CountRow]
    by_route: list[CountRow]  # the busiest routes
    by_district: list[CountRow]
    by_month: list[MonthRow]
    duplicates: int  # complaints marked as a duplicate of an earlier case
    incomplete: int
    failed_verification: int  # the bus could not be verified against the daily records
    non_operating: int  # the bus did not operate, or the trip was cancelled, on the reported date
