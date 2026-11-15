"""Data-quality checks and statistics for a synthetic batch. Everything is read from the database, not from memory."""

from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.orm import Session

ALLOWED_TRANSITIONS = {
    ("draft", "incomplete"), ("draft", "forwarded"), ("draft", "rejected"),
    ("incomplete", "forwarded"), ("incomplete", "rejected"), ("forwarded", "under_review"),
}

# Each check counts the rows that break the rule; zero means it passes.
CHECKS: list[tuple[str, str]] = [
    ("Every trip's permit belongs to its bus",
     "SELECT count(*) FROM daily_trips t JOIN permits p ON p.id = t.permit_id "
     "WHERE t.synthetic_batch_id = :b AND p.vehicle_id <> t.vehicle_id"),
    ("Every trip runs the permit's route or an authorized route for that date",
     "SELECT count(*) FROM daily_trips t JOIN permits p ON p.id = t.permit_id "
     "WHERE t.synthetic_batch_id = :b AND t.route_stand_id IS DISTINCT FROM p.route_stand_id AND NOT EXISTS ("
     " SELECT 1 FROM route_authorizations a WHERE a.vehicle_id = t.vehicle_id AND a.route_stand_id = t.route_stand_id"
     " AND a.valid_from <= t.service_date AND (a.valid_to IS NULL OR a.valid_to >= t.service_date))"),
    ("Trip times are consistent (arrival after departure, actual times only on trips that ran)",
     "SELECT count(*) FROM daily_trips t WHERE t.synthetic_batch_id = :b AND ("
     " t.end_time <= t.departure_time"
     " OR (t.trip_status = 'cancelled' AND (t.actual_departure IS NOT NULL OR t.actual_arrival IS NOT NULL))"
     " OR (t.trip_status <> 'cancelled' AND (t.actual_departure IS NULL OR t.actual_arrival IS NULL"
     "     OR t.actual_arrival <= t.actual_departure)))"),
    ("No bus has overlapping scheduled or actual trips",
     "SELECT count(*) FROM daily_trips a JOIN daily_trips b ON a.vehicle_id = b.vehicle_id AND a.service_date = b.service_date"
     " AND a.id < b.id WHERE a.synthetic_batch_id = :b AND b.synthetic_batch_id = :b AND ("
     " (a.departure_time < b.end_time AND b.departure_time < a.end_time)"
     " OR (a.trip_status <> 'cancelled' AND b.trip_status <> 'cancelled'"
     "     AND a.actual_departure < b.actual_arrival AND b.actual_departure < a.actual_arrival))"),
    ("No driver has overlapping duty blocks",
     "WITH d AS (SELECT DISTINCT t.service_date AS day, x.driver_person_id AS p, x.driver_start AS s, x.driver_end AS e"
     " FROM trip_duties x JOIN daily_trips t ON t.id = x.trip_id WHERE t.synthetic_batch_id = :b AND x.driver_person_id IS NOT NULL)"
     " SELECT count(*) FROM d a JOIN d c ON a.p = c.p AND a.day = c.day AND a.s < c.e AND c.s < a.e AND (a.s, a.e) <> (c.s, c.e)"),
    ("No conductor has overlapping duty blocks",
     "WITH d AS (SELECT DISTINCT t.service_date AS day, x.conductor_person_id AS p, x.conductor_start AS s, x.conductor_end AS e"
     " FROM trip_duties x JOIN daily_trips t ON t.id = x.trip_id WHERE t.synthetic_batch_id = :b AND x.conductor_person_id IS NOT NULL)"
     " SELECT count(*) FROM d a JOIN d c ON a.p = c.p AND a.day = c.day AND a.s < c.e AND c.s < a.e AND (a.s, a.e) <> (c.s, c.e)"),
    ("Duty intervals are valid (start before end)",
     "SELECT count(*) FROM trip_duties x JOIN daily_trips t ON t.id = x.trip_id WHERE t.synthetic_batch_id = :b AND"
     " ((x.driver_start IS NOT NULL AND x.driver_start >= x.driver_end) OR (x.conductor_start IS NOT NULL AND x.conductor_start >= x.conductor_end))"),
    ("Cancelled trips have no crew; trips that ran have a driver and a conductor",
     "SELECT count(*) FROM daily_trips t LEFT JOIN trip_duties x ON x.trip_id = t.id WHERE t.synthetic_batch_id = :b AND ("
     " (t.trip_status = 'cancelled' AND x.id IS NOT NULL) OR (t.trip_status <> 'cancelled' AND"
     "  (x.driver_person_id IS NULL OR x.conductor_person_id IS NULL)))"),
    ("Inactive buses have no trip that ran during an inactive period",
     "SELECT count(*) FROM daily_trips t JOIN bus_non_operations n ON n.vehicle_id = t.vehicle_id"
     " AND t.service_date BETWEEN n.start_date AND n.end_date"
     " WHERE t.synthetic_batch_id = :b AND n.synthetic_batch_id = :b AND t.trip_status IN ('completed', 'partial')"),
    ("Every trip's owner matches the published ownership for its date",
     "SELECT count(*) FROM daily_trips t WHERE t.synthetic_batch_id = :b AND NOT EXISTS ("
     " SELECT 1 FROM owner_assignments o WHERE o.vehicle_id = t.vehicle_id AND o.owner_person_id = t.owner_person_id"
     " AND o.status = 'published' AND o.valid_from <= t.service_date AND (o.valid_to IS NULL OR o.valid_to >= t.service_date))"),
    ("No bus has two owners at once",
     "SELECT count(*) FROM owner_assignments a JOIN owner_assignments c ON a.vehicle_id = c.vehicle_id AND a.id < c.id"
     " WHERE a.synthetic_batch_id = :b AND c.synthetic_batch_id = :b AND a.valid_from <= COALESCE(c.valid_to, 'infinity')"
     " AND c.valid_from <= COALESCE(a.valid_to, 'infinity')"),
    ("Complaints linked to a trip match its bus and date, and the trip ran unless it was cancelled",
     "SELECT count(*) FROM complaints c JOIN complaint_duty_snapshots s ON s.complaint_id = c.id"
     " JOIN daily_trips t ON t.id = s.trip_id WHERE c.synthetic_batch_id = :b AND ("
     " t.vehicle_id IS DISTINCT FROM c.vehicle_id OR t.service_date <> c.complaint_date"
     " OR (c.bus_verification <> 'trip_cancelled' AND t.trip_status = 'cancelled'))"),
    ("Complaints with a verified or corrected bus have a trip snapshot",
     "SELECT count(*) FROM complaints c WHERE c.synthetic_batch_id = :b AND c.bus_verification IN ('verified', 'corrected')"
     " AND NOT EXISTS (SELECT 1 FROM complaint_duty_snapshots s WHERE s.complaint_id = c.id)"),
    ("Wrong-number complaints keep the number as reported, apart from the corrected bus",
     "SELECT count(*) FROM complaints c JOIN synthetic_complaint_events e ON e.complaint_id = c.id AND e.event = 'bus_verification'"
     " LEFT JOIN vehicles v ON v.id = c.vehicle_id WHERE c.synthetic_batch_id = :b AND e.details ? 'mistake' AND ("
     " c.vehicle_number_entered IS NULL OR (v.id IS NOT NULL AND c.vehicle_number_entered = v.vehicle_number)"
     " OR (c.bus_verification = 'not_found' AND c.vehicle_id IS NOT NULL))"),
    ("Non-operating-bus complaints are flagged correctly",
     "SELECT count(*) FROM complaints c WHERE c.synthetic_batch_id = :b AND ("
     " (c.bus_verification = 'not_operated' AND EXISTS (SELECT 1 FROM daily_trips t WHERE t.vehicle_id = c.vehicle_id"
     "   AND t.service_date = c.complaint_date AND t.trip_status IN ('completed', 'partial')))"
     " OR (c.bus_verification = 'trip_cancelled' AND NOT EXISTS (SELECT 1 FROM daily_trips t WHERE t.vehicle_id = c.vehicle_id"
     "   AND t.service_date = c.complaint_date AND t.trip_status = 'cancelled')))"),
    ("Duplicate relationships link two complaints about the same bus, the earlier one first",
     "SELECT count(*) FROM duplicate_checks d JOIN complaints a ON a.id = d.complaint_id JOIN complaints b ON b.id = d.candidate_complaint_id"
     " JOIN synthetic_complaint_events ea ON ea.complaint_id = a.id AND ea.seq = 0"
     " JOIN synthetic_complaint_events eb ON eb.complaint_id = b.id AND eb.seq = 0"
     " WHERE a.synthetic_batch_id = :b AND (a.vehicle_id IS DISTINCT FROM b.vehicle_id OR eb.occurred_at > ea.occurred_at)"),
    ("A complaint rejected as a duplicate points at an earlier case",
     "SELECT count(*) FROM complaints c WHERE c.synthetic_batch_id = :b AND c.rejection_type = 'duplicate'"
     " AND (c.duplicate_of_complaint_id IS NULL OR c.duplicate_of_complaint_id >= c.id)"),
    ("Status histories start as a draft, follow the allowed transitions and end at the complaint's status",
     "WITH ev AS (SELECT e.*, lag(e.to_status) OVER (PARTITION BY e.complaint_id ORDER BY e.seq) AS prev,"
     " lag(e.occurred_at) OVER (PARTITION BY e.complaint_id ORDER BY e.seq) AS prev_at"
     " FROM synthetic_complaint_events e WHERE e.synthetic_batch_id = :b AND e.event IN ('created', 'status_change'))"
     " SELECT (SELECT count(*) FROM ev WHERE event = 'status_change' AND (from_status IS DISTINCT FROM prev OR occurred_at < prev_at"
     "   OR (from_status, to_status) NOT IN (" + ", ".join(f"('{a}', '{b}')" for a, b in sorted(ALLOWED_TRANSITIONS)) + ")))"
     " + (SELECT count(*) FROM complaints c WHERE c.synthetic_batch_id = :b AND c.status::text <> ("
     "   SELECT to_status FROM synthetic_complaint_events x WHERE x.complaint_id = c.id AND x.event IN ('created', 'status_change')"
     "   ORDER BY seq DESC LIMIT 1))"),
    ("Complaint timestamps are the simulated times (created when the history starts, updated when it ends)",
     "SELECT count(*) FROM complaints c JOIN synthetic_complaint_events e0 ON e0.complaint_id = c.id AND e0.seq = 0"
     " WHERE c.synthetic_batch_id = :b AND (c.created_at <> e0.occurred_at OR c.updated_at <> ("
     "   SELECT x.occurred_at FROM synthetic_complaint_events x WHERE x.complaint_id = c.id AND x.event IN ('created', 'status_change')"
     "   ORDER BY x.seq DESC LIMIT 1))"),
    ("Complaints in a routed status have everything the lifecycle requires",
     "SELECT count(*) FROM complaints c WHERE c.synthetic_batch_id = :b AND c.status IN ('forwarded', 'under_review')"
     " AND (c.vehicle_id IS NULL OR c.assigned_l2_user_id IS NULL OR c.reference_number IS NULL OR c.forwarded_at IS NULL)"),
]


def run_checks(db: Session, batch_id: int) -> list[dict]:
    results = []
    for name, sql in CHECKS:
        bad = db.execute(text(sql), {"b": batch_id}).scalar() or 0
        results.append({"check": name, "violations": int(bad), "ok": bad == 0})
    results.extend(_dashboard_checks(db, batch_id))
    return results


def _dashboard_checks(db: Session, batch_id: int) -> list[dict]:
    """Dashboard totals must equal plain SQL aggregates, for every officer who entered synthetic complaints."""
    from app.services import l1_dashboard_service

    officers = db.execute(text("SELECT DISTINCT entered_by_user_id FROM complaints WHERE synthetic_batch_id = :b"), {"b": batch_id}).scalars().all()
    wrong = 0
    for officer_id in officers:
        shown = l1_dashboard_service._by_target(db, SimpleNamespace(id=officer_id))
        raw = dict(db.execute(text(
            "SELECT coalesce(t.code, 'unclassified'), count(*) FROM complaints c LEFT JOIN complaint_target_types t ON t.id = c.target_type_id"
            " WHERE c.entered_by_user_id = :o GROUP BY 1"), {"o": officer_id}).all())
        data = shown.model_dump() if hasattr(shown, "model_dump") else dict(shown)
        wrong += sum(1 for key, value in data.items() if raw.get(key, 0) != value)
    results = [{"check": "Dashboard target counts equal SQL aggregates for each officer", "violations": wrong, "ok": wrong == 0}]
    try:
        from app.services import l1_analytics_service
    except ImportError:
        return results
    mismatches = 0
    for officer_id in officers:
        data = l1_analytics_service.analytics(db, SimpleNamespace(id=officer_id))
        total = db.execute(text("SELECT count(*) FROM complaints WHERE entered_by_user_id = :o"), {"o": officer_id}).scalar()
        mismatches += int(sum(row.count for row in data.by_month) != total) + int(sum(row.count for row in data.by_category) != total)
    results.append({"check": "Analytics month and category totals equal the officer's complaint count",
                    "violations": mismatches, "ok": mismatches == 0})
    return results


def statistics(db: Session, batch_id: int) -> dict:
    def one(sql: str):
        return db.execute(text(sql), {"b": batch_id}).scalar()

    def many(sql: str) -> dict:
        return {str(k): v for k, v in db.execute(text(sql), {"b": batch_id}).all()}

    return {
        "routes_with_trips": one("SELECT count(DISTINCT route_stand_id) FROM daily_trips WHERE synthetic_batch_id = :b"),
        "buses_with_trips": one("SELECT count(DISTINCT vehicle_id) FROM daily_trips WHERE synthetic_batch_id = :b"),
        "permits_used": one("SELECT count(DISTINCT permit_id) FROM daily_trips WHERE synthetic_batch_id = :b"),
        "owners": one("SELECT count(*) FROM people WHERE synthetic_batch_id = :b AND person_type = 'owner'"),
        "drivers": one("SELECT count(*) FROM people WHERE synthetic_batch_id = :b AND person_type = 'driver'"),
        "conductors": one("SELECT count(*) FROM people WHERE synthetic_batch_id = :b AND person_type = 'conductor'"),
        "operating_days": one("SELECT count(DISTINCT (vehicle_id, service_date)) FROM daily_trips WHERE synthetic_batch_id = :b AND trip_status <> 'cancelled'"),
        "trips": one("SELECT count(*) FROM daily_trips WHERE synthetic_batch_id = :b"),
        "cancelled_trips": one("SELECT count(*) FROM daily_trips WHERE synthetic_batch_id = :b AND trip_status = 'cancelled'"),
        "inactive_bus_days": one("SELECT coalesce(sum(end_date - start_date + 1), 0) FROM bus_non_operations WHERE synthetic_batch_id = :b"),
        "complaints": one("SELECT count(*) FROM complaints WHERE synthetic_batch_id = :b"),
        "by_target": many("SELECT coalesce(t.code, 'unclassified'), count(*) FROM complaints c LEFT JOIN complaint_target_types t ON t.id = c.target_type_id WHERE c.synthetic_batch_id = :b GROUP BY 1 ORDER BY 2 DESC"),
        "by_category": many("SELECT coalesce(k.name, 'none'), count(*) FROM complaints c LEFT JOIN complaint_categories k ON k.id = c.category_id WHERE c.synthetic_batch_id = :b GROUP BY 1 ORDER BY 2 DESC"),
        "duplicate_complaints": one("SELECT count(DISTINCT complaint_id) FROM duplicate_checks WHERE link_type = 'duplicate_of' AND complaint_id IN (SELECT id FROM complaints WHERE synthetic_batch_id = :b)"),
        "related_or_not_duplicate_links": one("SELECT count(*) FROM duplicate_checks WHERE link_type <> 'duplicate_of' AND complaint_id IN (SELECT id FROM complaints WHERE synthetic_batch_id = :b)"),
        "wrong_bus_number_complaints": one("SELECT count(*) FROM complaints WHERE synthetic_batch_id = :b AND id IN (SELECT complaint_id FROM synthetic_complaint_events WHERE details ? 'mistake')"),
        "non_operating_bus_complaints": one("SELECT count(*) FROM complaints WHERE synthetic_batch_id = :b AND bus_verification IN ('not_operated', 'trip_cancelled')"),
        "verification_failures": one("SELECT count(*) FROM complaints WHERE synthetic_batch_id = :b AND bus_verification IN ('not_found', 'not_operated', 'trip_cancelled', 'unverified')"),
        "by_status": many("SELECT status, count(*) FROM complaints WHERE synthetic_batch_id = :b GROUP BY 1 ORDER BY 2 DESC"),
        "by_district": many("SELECT coalesce(a.name, 'unknown'), count(*) FROM complaints c LEFT JOIN areas a ON a.id = c.area_id WHERE c.synthetic_batch_id = :b GROUP BY 1 ORDER BY 2 DESC"),
        "complaints_by_route_top10": many("SELECT coalesce(r.name, 'none'), count(*) FROM complaints c LEFT JOIN routes_stands r ON r.id = c.route_stand_id WHERE c.synthetic_batch_id = :b GROUP BY 1 ORDER BY 2 DESC LIMIT 10"),
    }
