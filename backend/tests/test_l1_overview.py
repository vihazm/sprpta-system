"""The lower dashboard cards (sources, passed to Level 2, transport and severity, recently forwarded) and the analytics."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.enums import ComplaintStatus, PlaceKind, VehicleType
from app.core.roles import UserRole
from app.main import app
from app.models import Area, Complaint, ComplaintMedium, RouteStand, Vehicle
from tests.conftest import make_user, sign_in
from tests.test_l1_dashboard import DASHBOARD, NOW, add, world  # noqa: F401  (the dashboard tests' master data)

OVERVIEW = f"{DASHBOARD}/overview"
ANALYTICS = f"{DASHBOARD}/analytics"


def forwarded(db, world, *, subject, minutes_ago=0, phone=None, by=None, **fields) -> Complaint:
    """A complaint forwarded to the Galle officer, with everything a routed complaint needs."""
    return add(
        db, by=by or world.me, status=ComplaintStatus.FORWARDED, subject=subject, medium_id=world.medium.id,
        category_id=world.category.id, severity_id=world.severity.id, vehicle_id=world.bus.id, area_id=world.area.id,
        assigned_l2_user_id=world.officer.id, forwarded_at=NOW - timedelta(minutes=minutes_ago), contact_phone=phone,
        **fields,
    )


def test_only_level_one_staff_may_read_the_overview_and_it_is_not_cached(client, db, world):
    assert client.get(OVERVIEW).headers["cache-control"] == "no-store"
    assert TestClient(app).get(OVERVIEW).status_code == 401
    for login, role in (("admin@sprpta.test", UserRole.ADMIN), ("chair@sprpta.test", UserRole.L3)):
        make_user(db, login, role)
        other = TestClient(app)
        sign_in(other, login)
        assert other.get(OVERVIEW).status_code == 403
    area = TestClient(app)
    sign_in(area, "ruwan@sprpta.test")
    assert area.get(OVERVIEW).status_code == 403


def test_with_nothing_entered_the_overview_is_empty_but_complete(client, db, world):
    body = client.get(OVERVIEW).json()
    assert body["month_total"] == 0 and body["sources"] == [] and body["forwarded"] == []
    assert body["busiest_week"] == {"medium": None, "count": 0, "total": 0}
    assert body["areas"] == [{"name": "Galle", "count": 0, "has_officer": True}]
    assert body["forwarded_total"] == 0 and body["transport"] == {"bus": 0, "trishaw": 0, "unknown": 0}
    assert [(s["severity"], s["count"]) for s in body["severity"]] == [("critical", 0), ("high", 0), ("medium", 0), ("low", 0)]


def test_the_overview_counts_this_officers_work_this_month(client, db, world):
    forwarded(db, world, subject="Sent on", phone="+94771234567")
    add(db, by=world.me, subject="Started on the phone")  # a draft: no medium, vehicle or severity yet
    forwarded(db, world, subject="Another officer's", by=world.other)  # not mine
    month_ago = 40 * 24 * 60
    forwarded(db, world, subject="Last month's", minutes_ago=month_ago, created=NOW - timedelta(days=40))  # not this month
    body = client.get(OVERVIEW).json()

    assert body["month_total"] == 2
    assert body["sources"] == [{"label": "WhatsApp", "count": 1}, {"label": "Not recorded", "count": 1}]
    assert body["busiest_week"] == {"medium": "WhatsApp", "count": 1, "total": 2}
    assert body["transport"] == {"bus": 1, "trishaw": 0, "unknown": 1}
    assert {s["severity"]: s["count"] for s in body["severity"]} == {"critical": 0, "high": 1, "medium": 0, "low": 0}
    assert body["forwarded_total"] == 1
    assert body["areas"] == [{"name": "Galle", "count": 1, "has_officer": True}]


def test_an_area_without_a_level_two_officer_is_marked(client, db, world):
    db.add(Area(name="Hambantota"))
    db.commit()
    areas = {a["name"]: a for a in client.get(OVERVIEW).json()["areas"]}
    assert areas["Galle"]["has_officer"] is True and areas["Hambantota"]["has_officer"] is False
    world.officer.is_active = False  # an inactive officer does not cover the area
    db.commit()
    assert {a["name"]: a["has_officer"] for a in client.get(OVERVIEW).json()["areas"]}["Galle"] is False


def test_the_trishaw_count_follows_the_vehicle_type(client, db, world):
    trishaw = Vehicle(vehicle_number="TR-0001", vehicle_type=VehicleType.TRISHAW, registered_area_id=world.area.id)
    db.add(trishaw)
    db.commit()
    add(db, by=world.me, subject="Meter", vehicle_id=trishaw.id)
    forwarded(db, world, subject="Bus")
    assert client.get(OVERVIEW).json()["transport"] == {"bus": 1, "trishaw": 1, "unknown": 0}


def test_recently_forwarded_is_the_latest_four_newest_first_with_the_contact_noted(client, db, world):
    for n, minutes in enumerate((50, 40, 30, 20, 10)):
        forwarded(db, world, subject=f"Case {n}", minutes_ago=minutes, phone="+94771234567" if n == 4 else None)
    shown = client.get(OVERVIEW).json()["forwarded"]
    assert [f["title"] for f in shown] == ["Case 4", "Case 3", "Case 2", "Case 1"]
    assert shown[0]["has_contact"] is True and shown[1]["has_contact"] is False
    assert shown[0]["severity"] == "high" and shown[0]["area_name"] == "Galle" and shown[0]["reference_number"]


def test_an_unknown_medium_is_counted_as_not_recorded_not_dropped(client, db, world):
    add(db, by=world.me, subject="No medium")
    add(db, by=world.me, subject="Also none")
    assert client.get(OVERVIEW).json()["sources"] == [{"label": "Not recorded", "count": 2}]


# ---------------------------------------------------------------- analytics


def test_a_complaint_with_no_route_is_not_listed_as_a_route(client, db, world):
    route = RouteStand(kind=PlaceKind.ROUTE, name="24/1 Avithtawa - Elpitiya", area_id=world.area.id)
    db.add(route)
    db.commit()
    add(db, by=world.me, subject="On a route", route_stand_id=route.id)
    add(db, by=world.me, subject="No route yet")
    body = client.get(ANALYTICS).json()
    assert body["total"] == 2  # both are still counted in the totals
    assert body["by_route"] == [{"id": route.id, "name": "24/1 Avithtawa - Elpitiya", "count": 1}]
