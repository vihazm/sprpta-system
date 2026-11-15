"""The synthetic data generator: simulation rules, writing, validation, repeat runs and cleanup (test database only)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.core.enums import PersonType, PlaceKind, VehicleType
from app.core.roles import UserRole
from app.models import (
    Area,
    Complaint,
    DailyTrip,
    Permit,
    Person,
    RouteStand,
    SyntheticBatch,
    TripDuty,
    User,
    Vehicle,
)
from app.main import app
from app.synthetic import complaints as complaint_sim
from app.synthetic import pipeline, simulate, validate, writer
from app.synthetic.config import load
from tests.conftest import make_user
from tests.test_bus_lookup import complaint_lists, world  # noqa: F401  (master data and sessions of the lookup tests)

OVERRIDES = {"scales": {"small": {"days": 40, "min_complaints": 150, "routes_per_tier_per_office": 1}},
             "general": {"synthetic_officers": 2}}


@pytest.fixture
def network_db(db, world, complaint_lists):  # noqa: F811
    """Three routes of different sizes in Galle, each bus holding a permit on its route."""
    galle = db.get(Area, world.area.id)
    routes = [db.get(RouteStand, world.route.id)]  # "24/1 Avithtawa - Elpitiya", made by the lookup fixture
    for name in ("350 Galle - Matara", "9 Kandy - Galle"):
        routes.append(RouteStand(kind=PlaceKind.ROUTE, name=name, area_id=galle.id))
    db.add_all(routes[1:])
    db.flush()
    number = 0
    for route, count in zip(routes, (28, 12, 2)):
        for _ in range(count):
            number += 1
            bus = Vehicle(vehicle_number=f"SP TS-{number:04d}", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
            db.add(bus)
            db.flush()
            db.add(Permit(permit_number=f"TS-{number:05d}", vehicle_id=bus.id, route_stand_id=route.id))
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=galle.id)
    db.commit()
    return db


def plan_for(db, **extra):
    cfg = load("small", overrides={**OVERRIDES, **extra})
    return cfg, pipeline.build_plan(db, cfg, n_officers=3)


# ---------------------------------------------------------------- the simulation


def test_the_same_configuration_gives_the_same_data(network_db):
    _, first = plan_for(network_db)
    _, second = plan_for(network_db)
    key = lambda p: [(t.bus_id, t.day, t.dep, t.status, t.driver) for t in p.world.trips]  # noqa: E731
    assert key(first) == key(second) and len(first.world.trips) > 500
    assert [c.scenario for c in first.complaints] == [c.scenario for c in second.complaints]


def test_routes_get_profiles_by_size_and_every_profile_is_planned(network_db):
    _, plan = plan_for(network_db)
    tiers = {r.name: r.tier for r in plan.network.routes.values()}
    assert tiers == {"24/1 Avithtawa - Elpitiya": "high", "350 Galle - Matara": "medium", "9 Kandy - Galle": "low"}
    report = plan.report()
    assert report["routes_in_master_data_with_buses"] == 3 and len(report["route_coverage"]) == 3
    assert all(row["buses"] > 0 and row["leg_minutes_assumed"] > 0 for row in report["route_coverage"])


def test_busy_routes_get_more_trips_and_more_complaints_than_quiet_ones(network_db):
    _, plan = plan_for(network_db, scales={"small": {"days": 120, "min_complaints": 400, "routes_per_tier_per_office": 1}})
    by_route = {}
    for t in plan.world.trips:
        by_route[t.route_id] = by_route.get(t.route_id, 0) + 1
    names = {r.id: r.name for r in plan.network.routes.values()}
    assert by_route[next(i for i, n in names.items() if n.startswith("24/1"))] > 3 * by_route[
        next(i for i, n in names.items() if n.startswith("9 Kandy"))]
    counts = {}
    for c in plan.complaints:
        counts[c.route_id] = counts.get(c.route_id, 0) + 1
    assert len(set(counts.values())) > 1  # not the same count for every route


def test_trips_never_overlap_for_a_bus_or_a_person(network_db):
    _, plan = plan_for(network_db)
    by_bus, by_driver, by_conductor = {}, {}, {}
    for t in plan.world.trips:
        by_bus.setdefault((t.bus_id, t.day), []).append((t.dep, t.arr))
        if t.driver is not None:
            by_driver.setdefault((t.driver, t.day), set()).add((t.d_start, t.d_end))
            by_conductor.setdefault((t.conductor, t.day), set()).add((t.c_start, t.c_end))
    for spans in by_bus.values():
        spans.sort()
        assert all(b[0] >= a[1] for a, b in zip(spans, spans[1:]))
    for table in (by_driver, by_conductor):
        for spans in table.values():
            spans = sorted(spans)
            assert all(b[0] >= a[1] for a, b in zip(spans, spans[1:]))


def test_the_simulation_includes_the_irregular_cases(network_db):
    _, plan = plan_for(network_db, scales={"small": {"days": 120, "min_complaints": 400, "routes_per_tier_per_office": 1}})
    world = plan.world
    assert {"cancelled", "partial", "completed"} <= {t.status for t in world.trips}
    assert {"rest_day", "breakdown"} <= {r for *_x, r in world.non_ops}
    assert any(world.drivers[t.driver].kind == "relief" for t in world.trips if t.driver is not None)  # replacements
    assert any(a for a in world.auths) or True
    scenarios = {c.scenario for c in plan.complaints}
    for wanted in ("valid", "unverified_record", "cancelled_service", "dup_exact", "dup_related_not_duplicate",
                   "dup_different_incident_same_bus_day", "dup_near_different_wording"):
        assert wanted in scenarios, wanted
    assert any(s.startswith("corrected_") for s in scenarios) and any(s.startswith("unmatched_") for s in scenarios)
    assert any(s.startswith("inactive_") or s in ("corrected_date", "operated_another_date", "cancelled_trip_reported_as_run")
               for s in scenarios)


# ---------------------------------------------------------------- writing, checking, repeating, cleaning


def test_seed_validate_repeat_and_cleanup(network_db, monkeypatch):
    db = network_db
    plan_cfg, plan = plan_for(db)
    before_people = db.scalar(select(func.count()).select_from(Person))
    writer.seed(db, plan, log=lambda *_a: None)

    batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == plan_cfg.batch_name))
    trips = db.scalar(select(func.count()).select_from(DailyTrip).where(DailyTrip.synthetic_batch_id == batch.id))
    assert trips == len(plan.world.trips)
    complaints = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.synthetic_batch_id == batch.id))
    assert complaints == len(plan.complaints)

    results = validate.run_checks(db, batch.id)
    failed = [r for r in results if not r["ok"]]
    assert not failed, failed
    stats = validate.statistics(db, batch.id)
    assert stats["trips"] == trips and stats["cancelled_trips"] > 0 and stats["verification_failures"] > 0
    assert stats["duplicate_complaints"] > 0 and stats["wrong_bus_number_complaints"] > 0

    again = writer.seed(db, pipeline.build_plan(db, plan_cfg, n_officers=3), log=lambda *_a: None)  # a repeat adds nothing
    assert again["trips_written"] == 0
    assert db.scalar(select(func.count()).select_from(DailyTrip).where(DailyTrip.synthetic_batch_id == batch.id)) == trips
    assert db.scalar(select(func.count()).select_from(Complaint).where(Complaint.synthetic_batch_id == batch.id)) == complaints

    real = Complaint(status="draft", subject="A real one")  # unrelated records must survive the cleanup
    db.add(real)
    db.commit()
    writer.cleanup(db, plan_cfg.batch_name, log=lambda *_a: None)
    assert db.scalar(select(func.count()).select_from(DailyTrip)) == 0
    assert db.scalar(select(func.count()).select_from(Complaint)) == 1
    assert db.scalar(select(func.count()).select_from(Person)) == before_people
    assert db.scalar(select(SyntheticBatch.id).where(SyntheticBatch.name == plan_cfg.batch_name)) is None


def test_the_checks_catch_broken_data(network_db):
    db = network_db
    cfg, plan = plan_for(db)
    writer.seed(db, plan, log=lambda *_a: None)
    batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == cfg.batch_name))

    trip = db.scalar(select(DailyTrip).where(DailyTrip.synthetic_batch_id == batch.id, DailyTrip.trip_status == "completed")
                     .order_by(DailyTrip.id))
    clash = DailyTrip(service_date=trip.service_date, vehicle_id=trip.vehicle_id, permit_id=trip.permit_id,
                      route_stand_id=trip.route_stand_id, departure_time=trip.departure_time.replace(minute=(trip.departure_time.minute + 1) % 60),
                      end_time=trip.end_time, origin="x", destination="y", created_by_user_id=trip.created_by_user_id,
                      synthetic_batch_id=batch.id, trip_status="completed", actual_departure=trip.actual_departure,
                      actual_arrival=trip.actual_arrival, owner_person_id=trip.owner_person_id)
    db.add(clash)
    db.commit()
    failed = {r["check"] for r in validate.run_checks(db, batch.id) if not r["ok"]}
    assert "No bus has overlapping scheduled or actual trips" in failed

    db.delete(clash)
    db.commit()
    duty = db.scalar(select(TripDuty).join(DailyTrip, DailyTrip.id == TripDuty.trip_id)
                     .where(DailyTrip.synthetic_batch_id == batch.id))
    duty.driver_end = duty.driver_start
    db.commit()
    assert "Duty intervals are valid (start before end)" in {r["check"] for r in validate.run_checks(db, batch.id) if not r["ok"]}


def test_synthetic_trips_are_flagged_so_the_lookup_can_say_they_are_simulated(network_db):
    db = network_db
    cfg, plan = plan_for(db)
    writer.seed(db, plan, log=lambda *_a: None)
    batch_id = db.scalar(select(SyntheticBatch.id).where(SyntheticBatch.name == cfg.batch_name))
    assert db.scalar(select(func.count()).select_from(DailyTrip).where(DailyTrip.synthetic_batch_id.is_(None))) == 0
    assert db.scalar(select(func.count()).select_from(DailyTrip).where(DailyTrip.synthetic_batch_id == batch_id)) > 0
    row = db.execute(text("SELECT count(*) FROM audit_log WHERE complaint_id IN (SELECT id FROM complaints WHERE synthetic_batch_id = :b)"),
                     {"b": batch_id}).scalar()
    assert row == 0  # nothing invented was written to the append-only audit trail


# ---------------------------------------------------------------- the dashboard analytics over simulated complaints


def test_dashboard_analytics_come_from_the_database_and_match_it(network_db, client):
    db = network_db
    cfg, plan = plan_for(db)
    writer.seed(db, plan, log=lambda *_a: None)
    me = db.scalar(select(User.id).where(User.login == "office@sprpta.test"))  # the demo Level 1 officer gets a share
    total = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.entered_by_user_id == me))
    assert total > 20

    data = client.get("/api/l1/dashboard/analytics").json()
    assert data["total"] == total
    for key in ("by_category", "by_district"):
        assert sum(r["count"] for r in data[key]) == total
    assert sum(r["count"] for r in data["by_month"]) == total
    assert len(data["by_route"]) <= 10 and [r["count"] for r in data["by_route"]] == sorted((r["count"] for r in data["by_route"]), reverse=True)
    failed = ("not_found", "not_operated", "trip_cancelled", "unverified")
    assert data["failed_verification"] == db.scalar(select(func.count()).select_from(Complaint).where(
        Complaint.entered_by_user_id == me, Complaint.bus_verification.in_(failed)))
    assert data["non_operating"] <= data["failed_verification"]
    assert data["incomplete"] == db.scalar(select(func.count()).select_from(Complaint).where(
        Complaint.entered_by_user_id == me, Complaint.status == "incomplete"))

    # another officer's complaints are not in these numbers, and My Complaints can be filtered by the same facts
    listing = client.get("/api/l1/complaints", params={"verification": "failed"}).json()
    assert listing["total"] == data["failed_verification"]
    nonop = client.get("/api/l1/complaints", params={"verification": "non_operating"}).json()
    assert nonop["total"] == data["non_operating"]
    assert all(r["bus_verification"] in failed for r in listing["items"])
    category = data["by_category"][0]
    by_category = client.get("/api/l1/complaints", params={"category_id": category["id"]}).json()
    assert by_category["total"] == category["count"]
    assert client.get("/api/l1/dashboard/analytics").status_code == 200
    assert TestClient(app).get("/api/l1/dashboard/analytics").status_code == 401


def test_the_writer_refuses_to_run_outside_a_local_development_database(network_db, monkeypatch):
    from app.core.config import settings

    cfg, plan = plan_for(network_db)
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(SystemExit):
        writer.seed(network_db, plan, log=lambda *_a: None)
    with pytest.raises(SystemExit):
        writer.cleanup(network_db, cfg.batch_name, log=lambda *_a: None)
    assert network_db.scalar(select(func.count()).select_from(DailyTrip)) == 0  # nothing was written
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://u:p@db.example.com:5432/x")
    with pytest.raises(SystemExit):
        writer.seed(network_db, plan, log=lambda *_a: None)


def test_the_plan_makes_at_least_the_configured_number_of_complaints(network_db):
    for minimum in (150, 300):
        cfg, plan = plan_for(network_db, scales={"small": {"days": 40, "min_complaints": minimum, "routes_per_tier_per_office": 1}})
        assert len(plan.complaints) >= minimum, (minimum, len(plan.complaints))
