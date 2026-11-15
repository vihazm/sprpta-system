"""Timing and index-use checks over a synthetic batch, using the same services the API calls (no network in the way).

Targets are for this development machine: they flag a query that has stopped using its index, not production speed.
"""

import statistics
import time
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Complaint, DailyTrip, SyntheticBatch, Vehicle
from app.services import bus_lookup_service, complaint_intake_service, complaint_list_service, l1_analytics_service, l1_dashboard_service

TARGET_MS = {"lookup": 150, "list": 400, "dashboard": 800, "analytics": 800, "duplicates": 400}


def _time(fn, runs: int = 5) -> tuple[float, float]:
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples), max(samples)


def _plan(db: Session, sql: str, **params) -> str:
    rows = db.execute(text("EXPLAIN (ANALYZE, FORMAT TEXT) " + sql), params).scalars().all()
    plan = "\n".join(rows)
    kind = "Seq Scan" if "Seq Scan" in plan else ("Index" if "Index" in plan else "other")
    return f"{kind}, {rows[-1].strip()}"


def run(db: Session, batch_name: str) -> list[dict]:
    batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == batch_name))
    if batch is None:
        raise SystemExit("There is no data for this batch.")
    trip = db.scalar(select(DailyTrip).where(DailyTrip.synthetic_batch_id == batch.id, DailyTrip.trip_status == "completed",
                                             DailyTrip.status == "published").order_by(DailyTrip.id.desc()))
    bus = db.get(Vehicle, trip.vehicle_id)
    officer_id = db.scalar(text("SELECT entered_by_user_id FROM complaints WHERE synthetic_batch_id = :b GROUP BY 1 ORDER BY count(*) DESC LIMIT 1"),
                           {"b": batch.id})
    officer = SimpleNamespace(id=officer_id)
    complaint_id = db.scalar(select(Complaint.id).where(Complaint.synthetic_batch_id == batch.id, Complaint.status == "draft",
                                                        Complaint.entered_by_user_id == officer_id).limit(1))
    category = db.scalar(select(Complaint.category_id).where(Complaint.synthetic_batch_id == batch.id).limit(1))
    results = []

    def check(name: str, group: str, fn) -> None:
        median, worst = _time(fn)
        results.append({"name": name, "median_ms": round(median, 1), "worst_ms": round(worst, 1),
                        "target_ms": TARGET_MS[group], "ok": median <= TARGET_MS[group]})

    check("Date + bus number lookup", "lookup", lambda: bus_lookup_service.search_trips(db, trip.service_date, bus.vehicle_number))
    check("Trip details", "lookup", lambda: bus_lookup_service.trip_details(db, trip.id))
    list_args = dict(status=None, target=None, scope="mine", officer_id=officer_id, search="", page=1)
    check("My Complaints, first page", "list", lambda: complaint_list_service.list_complaints(db, **list_args))
    check("My Complaints, page 20", "list", lambda: complaint_list_service.list_complaints(db, **{**list_args, "page": 20}))
    check("My Complaints, filtered by target", "list", lambda: complaint_list_service.list_complaints(db, **{**list_args, "target": "driver"}))
    check("My Complaints, filtered by issue category", "list", lambda: complaint_list_service.list_complaints(db, **{**list_args, "category_id": category}))
    check("My Complaints, bus verification failures", "list", lambda: complaint_list_service.list_complaints(db, **{**list_args, "verification": "failed"}))
    check("My Complaints, search by bus number", "list", lambda: complaint_list_service.list_complaints(db, **{**list_args, "search": bus.vehicle_number[-4:]}))
    check("Dashboard summary", "dashboard", lambda: l1_dashboard_service.dashboard(db, officer))
    check("Dashboard analytics", "analytics", lambda: l1_analytics_service.analytics(db, officer))
    if complaint_id:
        check("Duplicate check for a draft", "duplicates", lambda: complaint_intake_service.get_duplicates(db, complaint_id))

    plans = {
        "Lookup by date + bus": _plan(db, "SELECT * FROM daily_trips WHERE vehicle_id = :v AND service_date = :d AND status = 'published'",
                                      v=bus.id, d=trip.service_date),
        "Trips by route + date": _plan(db, "SELECT count(*) FROM daily_trips WHERE route_stand_id = :r AND service_date = :d",
                                       r=trip.route_stand_id, d=trip.service_date),
        "Complaints of one officer by target": _plan(db, "SELECT count(*) FROM complaints WHERE entered_by_user_id = :o AND target_type_id = 1", o=officer_id),
        "Complaints by category": _plan(db, "SELECT count(*) FROM complaints WHERE category_id = :c", c=category),
        "Complaints by incident date": _plan(db, "SELECT count(*) FROM complaints WHERE complaint_date = :d", d=trip.service_date),
        "Complaints by verification": _plan(db, "SELECT count(*) FROM complaints WHERE bus_verification = 'not_operated'"),
        "Driver duty rows": _plan(db, "SELECT count(*) FROM trip_duties WHERE driver_person_id = (SELECT driver_person_id FROM trip_duties LIMIT 1)"),
    }
    results.append({"plans": plans})
    return results
