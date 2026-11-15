from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.enums import DutyRecordStatus, PersonType, PlaceKind, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.main import app
from app.models import (
    AuditLog,
    Complaint,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintMedium,
    DailyTrip,
    Permit,
    Person,
    RouteStand,
    Severity,
    TripDuty,
    Vehicle,
)
from tests.conftest import make_user, sign_in, target_id

LOOKUP = "/api/l1/bus-lookup"
ADMIN = "/api/admin/duty-records"
TODAY = datetime.now(LOCAL).date()
DAY = TODAY - timedelta(days=1)  # the incident date used throughout


class World:
    """Master data, an Admin session (`admin`) and a Level 1 session (`client`)."""


@pytest.fixture
def world(db, client, galle) -> World:
    w = World()
    w.area = galle
    w.owner = Person(full_name="Nimal Perera", person_type=PersonType.OWNER)
    w.driver = Person(full_name="Saman Kumara", person_type=PersonType.DRIVER)
    w.conductor = Person(full_name="Chaminda Rathnayake", person_type=PersonType.CONDUCTOR)
    w.route = RouteStand(kind=PlaceKind.ROUTE, name="24/1 Avithtawa - Elpitiya", area_id=galle.id)
    db.add_all([w.owner, w.driver, w.conductor, w.route])
    db.flush()
    w.bus = Vehicle(
        vehicle_number="ND-7782", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, owner_person_id=w.owner.id
    )
    other = Vehicle(vehicle_number="ND-7980", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
    db.add_all([w.bus, other])
    db.flush()
    w.permit = Permit(permit_number="002108", vehicle_id=w.bus.id)
    w.other_permit = Permit(permit_number="002822", vehicle_id=other.id)
    db.add_all([w.permit, w.other_permit])
    db.commit()

    make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="Sarah Admin")
    make_user(db, "office@sprpta.test", UserRole.L1, full_name="Office Staff")
    w.admin = TestClient(app)
    sign_in(w.admin, "admin@sprpta.test")
    sign_in(client, "office@sprpta.test")
    return w


def trip_body(w: World, **changes) -> dict:
    body = {
        "service_date": DAY.isoformat(),
        "vehicle_number": "ND-7782",
        "route_stand_id": w.route.id,
        "departure_time": "06:30",
        "origin": "Avithtawa",
        "destination": "Elpitiya",
        "driver_person_id": w.driver.id,
        "conductor_person_id": w.conductor.id,
    }
    return {**body, **changes}


def publish_trip(w: World, **changes) -> dict:
    """A trip made, approved and published through the Admin API."""
    created = w.admin.post(f"{ADMIN}/trips", json=trip_body(w, **changes))
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]
    assert w.admin.post(f"{ADMIN}/trips/{trip_id}/approve").status_code == 200
    published = w.admin.post(f"{ADMIN}/trips/{trip_id}/publish")
    assert published.status_code == 200, published.text
    return published.json()


def search(client, bus="ND-7782", on=DAY):
    return client.get(f"{LOOKUP}/trips", params={"service_date": on.isoformat(), "bus_number": bus})


def error_code(response) -> str:
    return response.json()["detail"]["code"]


# ---------------------------------------------------------------- authorization


def test_only_level_one_staff_may_search(db, client, world):
    trip = publish_trip(world)
    assert world.admin.get(f"{LOOKUP}/trips", params={"service_date": DAY.isoformat(), "bus_number": "x"}).status_code == 403
    assert world.admin.get(f"{LOOKUP}/trips/{trip['id']}").status_code == 403
    make_user(db, "chair@sprpta.test", UserRole.L3)
    other = TestClient(app)
    sign_in(other, "chair@sprpta.test")
    assert search(other).status_code == 403
    assert TestClient(app).get(f"{LOOKUP}/trips/{trip['id']}").status_code == 401


def test_only_the_admin_may_manage_duty_records(client, world):
    owner_body = {"vehicle_number": "ND-7782", "owner_person_id": world.owner.id, "valid_from": DAY.isoformat()}
    for response in (
        client.get(f"{ADMIN}/trips"),
        client.post(f"{ADMIN}/trips", json=trip_body(world)),
        client.post(f"{ADMIN}/trips/1/approve"),
        client.post(f"{ADMIN}/trips/1/publish"),
        client.post(f"{ADMIN}/owner-assignments", json=owner_body),
        client.post(f"{ADMIN}/owner-assignments/1/approve"),
        client.post(f"{ADMIN}/owner-assignments/1/publish"),
    ):
        assert response.status_code == 403
    assert TestClient(app).get(f"{ADMIN}/trips").status_code == 401


# ---------------------------------------------------------------- Admin workflow


def test_a_record_reaches_level_one_only_once_it_is_published(client, world):
    created = world.admin.post(f"{ADMIN}/trips", json=trip_body(world))
    assert created.status_code == 201
    trip = created.json()
    assert (trip["status"], trip["duty_verified"], trip["permit_number"]) == ("draft", False, "002108")
    assert (trip["driver"], trip["conductor"]) == ("Saman Kumara", "Chaminda Rathnayake")

    assert search(client).json()["trips"] == []  # a draft is not visible
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").status_code == 404

    approved = world.admin.post(f"{ADMIN}/trips/{trip['id']}/approve").json()
    assert (approved["status"], approved["duty_verified"]) == ("approved", True)  # approving verifies the duty
    assert search(client).json()["trips"] == []  # approved is still not published

    published = world.admin.post(f"{ADMIN}/trips/{trip['id']}/publish").json()
    assert published["status"] == "published" and published["published_at"] is not None
    assert [t["id"] for t in search(client).json()["trips"]] == [trip["id"]]


def test_a_record_moves_one_step_at_a_time(world):
    trip = world.admin.post(f"{ADMIN}/trips", json=trip_body(world)).json()
    uri = f"{ADMIN}/trips/{trip['id']}"
    assert error_code(world.admin.post(f"{uri}/publish")) == "wrong_status"  # a draft cannot skip approval
    assert world.admin.post(f"{uri}/approve").status_code == 200
    assert error_code(world.admin.post(f"{uri}/approve")) == "wrong_status"
    assert world.admin.post(f"{uri}/publish").status_code == 200
    assert error_code(world.admin.post(f"{uri}/publish")) == "wrong_status"
    assert world.admin.post(f"{ADMIN}/trips/999999/approve").status_code == 404


def test_admin_steps_are_audited(db, world):
    publish_trip(world)
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "daily_trips").order_by(AuditLog.id)).all()
    assert actions == ["trip.create", "trip.approved", "trip.published"]
    assert db.scalar(select(AuditLog.actor_role).where(AuditLog.action == "trip.published")) == "admin"


def test_admin_can_list_trips_by_date_and_status(world):
    publish_trip(world)
    world.admin.post(f"{ADMIN}/trips", json=trip_body(world, departure_time="09:00"))
    publish_trip(world, service_date=(DAY - timedelta(days=3)).isoformat())
    everything = world.admin.get(f"{ADMIN}/trips").json()
    assert everything["total"] == 3
    on_day = world.admin.get(f"{ADMIN}/trips", params={"service_date": DAY.isoformat()}).json()
    assert [t["departure_time"] for t in on_day["items"]] == ["06:30:00", "09:00:00"]
    drafts = world.admin.get(f"{ADMIN}/trips", params={"status": "draft"}).json()
    assert drafts["total"] == 1 and drafts["items"][0]["departure_time"] == "09:00:00"


def test_trips_are_checked_when_they_are_added(world, db):
    cases = {
        "unknown_vehicle": trip_body(world, vehicle_number="XX-0000"),
        "unknown_route": trip_body(world, route_stand_id=9999),
        "unknown_driver": trip_body(world, driver_person_id=world.conductor.id),  # a conductor is not a driver
        "unknown_conductor": trip_body(world, conductor_person_id=world.driver.id),
        "permit_mismatch": trip_body(world, permit_number="002822"),  # that permit is another bus's
    }
    for code, body in cases.items():
        response = world.admin.post(f"{ADMIN}/trips", json=body)
        assert response.status_code == 422 and error_code(response) == code, code
    db.add(Vehicle(vehicle_number="ND-1111", vehicle_type=VehicleType.BUS, registered_area_id=world.area.id))
    db.commit()
    no_permit = world.admin.post(f"{ADMIN}/trips", json=trip_body(world, vehicle_number="ND-1111"))
    assert no_permit.status_code == 422 and error_code(no_permit) == "no_permit"
    assert world.admin.post(f"{ADMIN}/trips", json=trip_body(world, origin="  ")).status_code == 422

    assert world.admin.post(f"{ADMIN}/trips", json=trip_body(world)).status_code == 201
    again = world.admin.post(f"{ADMIN}/trips", json=trip_body(world))
    assert again.status_code == 409 and error_code(again) == "duplicate_trip"


# ---------------------------------------------------------------- search


def test_search_lists_the_published_trips_of_that_bus_on_that_date(client, world):
    late = publish_trip(world, departure_time="14:15")
    early = publish_trip(world, departure_time="06:30")
    publish_trip(world, vehicle_number="ND-7980")  # another bus, same day
    publish_trip(world, service_date=(DAY - timedelta(days=1)).isoformat())  # same bus, another day

    body = search(client, "nd 7782").json()  # case, spaces and hyphens do not matter
    assert [t["id"] for t in body["trips"]] == [early["id"], late["id"]]  # by departure time
    assert body["trips"][0] == {
        "id": early["id"],
        "bus_number": "ND-7782",
        "permit_number": "002108",
        "route": "24/1 Avithtawa - Elpitiya",
        "departure_time": "06:30:00",
        "trip_status": "completed",
        "direction": None,
        "synthetic": False,
    }
    assert body["service_date"] == DAY.isoformat()
    assert body["vehicle"]["area_name"] == "Galle" and body["vehicle"]["permit_number"] == "002108"


def test_search_with_no_published_record_returns_an_empty_list_for_a_known_bus(client, world):
    body = search(client)
    assert body.status_code == 200
    assert body.json()["trips"] == [] and body.json()["vehicle"]["vehicle_number"] == "ND-7782"


def test_search_is_checked(client, world):
    unknown = search(client, "XX-0000")
    assert unknown.status_code == 404 and error_code(unknown) == "vehicle_not_found"
    future = search(client, on=TODAY + timedelta(days=1))
    assert future.status_code == 422 and error_code(future) == "future_date"
    assert search(client, on=TODAY).status_code == 200  # today is allowed
    assert client.get(f"{LOOKUP}/trips", params={"bus_number": "ND-7782"}).status_code == 422  # the date is required
    assert client.get(f"{LOOKUP}/trips", params={"service_date": "2026-13-45", "bus_number": "x"}).status_code == 422
    assert client.get(f"{LOOKUP}/trips", params={"service_date": DAY.isoformat(), "bus_number": ""}).status_code == 422
    assert client.get(f"{LOOKUP}/trips/999999").status_code == 404


def test_changing_the_date_changes_the_results(client, world):
    publish_trip(world)
    assert len(search(client).json()["trips"]) == 1
    assert search(client, on=DAY - timedelta(days=1)).json()["trips"] == []


# ---------------------------------------------------------------- the selected record


def test_the_selected_record_shows_everything_that_was_verified(client, world):
    trip = publish_trip(world)
    details = client.get(f"{LOOKUP}/trips/{trip['id']}")
    assert details.status_code == 200
    assert details.json() == {
        "trip_id": trip["id"],
        "service_date": DAY.isoformat(),
        "vehicle_id": world.bus.id,
        "bus_number": "ND-7782",
        "area_id": world.area.id,
        "area_name": "Galle",
        "permit_id": world.permit.id,
        "permit_number": "002108",
        "route_stand_id": world.route.id,
        "route": "24/1 Avithtawa - Elpitiya",
        "origin": "Avithtawa",
        "destination": "Elpitiya",
        "departure_time": "06:30:00",
        "arrival_time": None,
        "actual_departure": None,
        "actual_arrival": None,
        "trip_status": "completed",
        "direction": None,
        "synthetic": False,
        "owner": {"person_id": world.owner.id, "name": "Nimal Perera", "source": "vehicle_record"},
        "driver": {"person_id": world.driver.id, "name": "Saman Kumara", "status": "verified"},
        "conductor": {"person_id": world.conductor.id, "name": "Chaminda Rathnayake", "status": "verified"},
        "verification_status": "Verified",
    }


def test_a_trip_without_a_duty_record_is_unavailable_and_nobody_is_guessed(client, world):
    trip = publish_trip(world, driver_person_id=None, conductor_person_id=None)
    body = client.get(f"{LOOKUP}/trips/{trip['id']}").json()
    assert body["verification_status"] == "Unavailable"
    assert body["driver"] == {"person_id": None, "name": None, "status": "unavailable"}
    assert body["conductor"] == {"person_id": None, "name": None, "status": "unavailable"}


def test_a_missing_conductor_does_not_make_a_verified_driver_unverified(client, world):
    trip = publish_trip(world, conductor_person_id=None)
    body = client.get(f"{LOOKUP}/trips/{trip['id']}").json()
    assert body["driver"]["status"] == "verified" and body["driver"]["name"] == "Saman Kumara"
    assert body["conductor"] == {"person_id": None, "name": None, "status": "unavailable"}  # nobody is guessed
    assert body["verification_status"] == "Verified"  # judged on the people the record names, here the driver


def test_unverified_staff_are_never_named(client, db, world):
    trip = publish_trip(world)
    duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == trip["id"]))
    duty.verified_by_user_id = duty.verified_at = None  # a record whose duty was never verified
    db.commit()
    body = client.get(f"{LOOKUP}/trips/{trip['id']}").json()
    for who in ("driver", "conductor"):
        assert body[who] == {"person_id": None, "name": None, "status": "unverified"}
    assert body["verification_status"] == "Unverified"


def test_a_missing_owner_is_unavailable(client, db, world):
    world.bus.owner_person_id = None
    db.commit()
    trip = publish_trip(world)
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").json()["owner"] == {
        "person_id": None, "name": None, "source": None,
    }


def test_the_owner_on_that_date_comes_from_the_published_ownership_record(client, db, world):
    new_owner = Person(full_name="Kamal Silva", person_type=PersonType.OWNER)
    db.add(new_owner)
    db.commit()
    trip = publish_trip(world)
    owner_of = lambda: client.get(f"{LOOKUP}/trips/{trip['id']}").json()["owner"]  # noqa: E731

    body = {"vehicle_number": "ND-7782", "owner_person_id": new_owner.id, "valid_from": (DAY - timedelta(days=5)).isoformat()}
    created = world.admin.post(f"{ADMIN}/owner-assignments", json=body)
    assert created.status_code == 201 and created.json()["status"] == "draft"
    assignment = created.json()["id"]
    assert owner_of()["name"] == "Nimal Perera"  # a draft is ignored

    assert world.admin.post(f"{ADMIN}/owner-assignments/{assignment}/approve").json()["status"] == "approved"
    assert owner_of()["name"] == "Nimal Perera"  # so is an approved one
    assert world.admin.post(f"{ADMIN}/owner-assignments/{assignment}/publish").json()["status"] == "published"
    assert owner_of() == {"person_id": new_owner.id, "name": "Kamal Silva", "source": "assignment"}

    # A period that ended before the incident date no longer applies.
    other_day = publish_trip(world, service_date=(DAY - timedelta(days=9)).isoformat())
    assert client.get(f"{LOOKUP}/trips/{other_day['id']}").json()["owner"]["name"] == "Nimal Perera"


def test_ownership_records_are_checked_and_move_one_step_at_a_time(world):
    uri = f"{ADMIN}/owner-assignments"
    body = {"vehicle_number": "ND-7782", "owner_person_id": world.owner.id, "valid_from": DAY.isoformat()}
    assert error_code(world.admin.post(uri, json={**body, "vehicle_number": "XX-0"})) == "unknown_vehicle"
    assert error_code(world.admin.post(uri, json={**body, "owner_person_id": world.driver.id})) == "unknown_owner"
    backwards = world.admin.post(uri, json={**body, "valid_to": (DAY - timedelta(days=1)).isoformat()})
    assert backwards.status_code == 422 and error_code(backwards) == "invalid_period"

    made = world.admin.post(uri, json=body).json()
    assert error_code(world.admin.post(f"{uri}/{made['id']}/publish")) == "wrong_status"
    assert world.admin.post(f"{uri}/999999/approve").status_code == 404


def test_a_record_that_is_not_published_cannot_be_selected(client, world):
    draft = world.admin.post(f"{ADMIN}/trips", json=trip_body(world)).json()
    assert client.get(f"{LOOKUP}/trips/{draft['id']}").status_code == 404


# ---------------------------------------------------------------- use the details in a complaint

COMPLAINTS = "/api/l1/complaints"


@pytest.fixture
def complaint_lists(db, world):
    db.add_all(
        [
            ComplaintMedium(name="WhatsApp"),
            ComplaintCategory(name="Overcharging"),
            Severity(name="High", rank=2, forward_days=1, decide_days=3, close_days=7, rating_weight=4),
        ]
    )
    db.commit()


def complaint_body(trip_id: int | None, **changes) -> dict:
    return {"trip_id": trip_id, "subject": "Charged more than the fare", **changes}


def snapshot_of(db, complaint_id: int) -> ComplaintDutySnapshot | None:
    db.expire_all()
    return db.scalar(select(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id == complaint_id))


def test_the_trip_reference_fills_the_complaint_from_the_database(client, db, world, complaint_lists):
    second = Permit(permit_number="002109", vehicle_id=world.bus.id)  # a bus with two permits
    db.add(second)
    db.commit()
    trip = publish_trip(world, permit_number="002109")

    created = client.post(COMPLAINTS, json=complaint_body(trip["id"]))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["trip_id"] == trip["id"] and body["vehicle_number"] == "ND-7782"
    assert (body["permit_id"], body["owner_person_id"], body["route_stand_id"]) == (
        second.id, world.owner.id, world.route.id,
    )
    assert body["complaint_date"] == DAY.isoformat() and body["area_name"] == "Galle"
    assert body["duty"] == {
        "trip_id": trip["id"],
        "service_date": DAY.isoformat(),
        "bus_number": "ND-7782",
        "permit_number": "002109",
        "route": "24/1 Avithtawa - Elpitiya",
        "origin": "Avithtawa",
        "destination": "Elpitiya",
        "departure_time": "06:30:00",
        "owner_person_id": world.owner.id,
        "owner_name": "Nimal Perera",
        "driver_person_id": world.driver.id,
        "driver_name": "Saman Kumara",
        "conductor_person_id": world.conductor.id,
        "conductor_name": "Chaminda Rathnayake",
        "verification_status": "Verified",
    }

    row = db.get(Complaint, body["id"])
    assert (row.permit_id, row.owner_person_id, row.route_stand_id) == (second.id, world.owner.id, world.route.id)
    snap = snapshot_of(db, body["id"])
    assert (snap.trip_id, snap.permit_number, snap.driver_person_id) == (trip["id"], "002109", world.driver.id)
    assert snap.verification_status == "Verified"


def test_nothing_about_the_bus_is_taken_from_the_request(client, db, world, complaint_lists):
    trip = publish_trip(world)
    other_route = RouteStand(kind=PlaceKind.ROUTE, name="Another route", area_id=world.area.id)
    db.add(other_route)
    db.commit()
    body = complaint_body(
        trip["id"],
        route_stand_id=other_route.id,
        complaint_date=TODAY.isoformat(),
        permit_id=world.other_permit.id,
        owner_person_id=world.driver.id,
        verification_status="Verified",
        driver_name="Somebody Else",
    )
    created = client.post(COMPLAINTS, json=body).json()
    assert created["route_stand_id"] == world.route.id  # the record's route, not the one sent
    assert created["complaint_date"] == DAY.isoformat()  # the record's date
    assert created["permit_id"] == world.permit.id and created["owner_person_id"] == world.owner.id
    assert created["duty"]["driver_name"] == "Saman Kumara"
    assert snapshot_of(db, created["id"]).driver_name == "Saman Kumara"


def test_reopening_a_saved_complaint_shows_the_same_bus_and_duty_details(client, db, world, complaint_lists):
    trip = publish_trip(world)
    saved = client.post(COMPLAINTS, json=complaint_body(trip["id"], incident_location="Galle stand")).json()
    again = client.get(f"{COMPLAINTS}/{saved['id']}").json()
    assert again["duty"] == saved["duty"] and again["trip_id"] == trip["id"]
    assert again["incident_location"] == "Galle stand"
    assert {c["id"] for c in client.get(COMPLAINTS).json()["items"]} == {saved["id"]}  # it is listed as an open draft


def test_the_snapshot_survives_the_record_being_withdrawn_or_corrected(client, db, world, complaint_lists):
    trip = publish_trip(world)
    saved = client.post(COMPLAINTS, json=complaint_body(trip["id"])).json()

    row = db.get(DailyTrip, trip["id"])
    row.status = DutyRecordStatus.APPROVED  # Admin withdrew it
    db.get(Person, world.driver.id).full_name = "Corrected Name"
    db.commit()

    kept = client.put(f"{COMPLAINTS}/{saved['id']}", json=complaint_body(trip["id"], subject="Changed")).json()
    assert kept["subject"] == "Changed" and kept["duty"]["driver_name"] == "Saman Kumara"  # as it was when saved
    fresh = client.post(COMPLAINTS, json=complaint_body(trip["id"]))
    assert fresh.status_code == 404 and error_code(fresh) == "trip_not_found"  # a new complaint cannot use it


def test_changing_the_selected_bus_replaces_its_details_and_clearing_it_removes_them(client, db, world, complaint_lists):
    first = publish_trip(world)
    second = publish_trip(world, vehicle_number="ND-7980", driver_person_id=None, conductor_person_id=None)
    uri = f"{COMPLAINTS}/{client.post(COMPLAINTS, json=complaint_body(first['id'])).json()['id']}"

    changed = client.put(uri, json=complaint_body(second["id"])).json()
    assert changed["vehicle_number"] == "ND-7980" and changed["trip_id"] == second["id"]
    assert changed["permit_id"] == world.other_permit.id and changed["owner_person_id"] is None
    assert changed["duty"]["driver_name"] is None and changed["duty"]["verification_status"] == "Unavailable"
    assert db.scalar(select(func.count()).select_from(ComplaintDutySnapshot)) == 1  # replaced, not added

    cleared = client.put(uri, json={"vehicle_number": "ND-7782", "subject": "Typed by hand"}).json()
    assert cleared["trip_id"] is None and cleared["duty"] is None
    assert cleared["permit_id"] == world.permit.id and cleared["owner_person_id"] == world.owner.id  # the bus's own
    assert db.scalar(select(func.count()).select_from(ComplaintDutySnapshot)) == 0
    actions = db.scalars(select(AuditLog.action).where(AuditLog.action.like("complaint.bus_%")).order_by(AuditLog.id)).all()
    assert actions == ["complaint.bus_selected", "complaint.bus_selected", "complaint.bus_cleared"]


def test_a_record_for_another_bus_is_refused(client, db, world, complaint_lists):
    trip = publish_trip(world)
    mismatch = client.post(COMPLAINTS, json=complaint_body(trip["id"], vehicle_number="ND-7980"))
    assert mismatch.status_code == 422 and error_code(mismatch) == "trip_mismatch"
    assert db.scalar(select(func.count()).select_from(Complaint)) == 0  # nothing half-saved
    same_bus = client.post(COMPLAINTS, json=complaint_body(trip["id"], vehicle_number="nd 7782"))
    assert same_bus.status_code == 201


def test_a_record_that_is_unpublished_or_unknown_cannot_be_used(client, world, complaint_lists):
    draft = world.admin.post(f"{ADMIN}/trips", json=trip_body(world)).json()
    for trip_id in (draft["id"], 999999):
        response = client.post(COMPLAINTS, json=complaint_body(trip_id))
        assert response.status_code == 404 and error_code(response) == "trip_not_found"
    assert client.post(COMPLAINTS, json=complaint_body(0)).status_code == 422


def test_missing_and_unverified_people_are_stored_as_such(client, db, world, complaint_lists):
    world.bus.owner_person_id = None
    db.commit()
    trip = publish_trip(world, conductor_person_id=None)
    duty = client.post(COMPLAINTS, json=complaint_body(trip["id"])).json()["duty"]
    assert (duty["owner_name"], duty["conductor_name"]) == (None, None)
    assert duty["driver_name"] == "Saman Kumara" and duty["verification_status"] == "Verified"

    unverified = publish_trip(world, departure_time="09:00")
    row = db.scalar(select(TripDuty).where(TripDuty.trip_id == unverified["id"]))
    row.verified_by_user_id = row.verified_at = None
    db.commit()
    duty = client.post(COMPLAINTS, json=complaint_body(unverified["id"])).json()["duty"]
    assert (duty["driver_name"], duty["conductor_name"]) == (None, None)  # never named while unverified


def test_the_saved_details_stay_with_a_forwarded_complaint(client, db, world, complaint_lists):
    trip = publish_trip(world)
    medium = db.scalar(select(ComplaintMedium))
    category = db.scalar(select(ComplaintCategory))
    severity = db.scalar(select(Severity))
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    body = complaint_body(
        trip["id"], medium_id=medium.id, category_id=category.id, severity_id=severity.id,
        complainant_name="Kamala Fernando", description="Asked for double the fare",
        target_type_id=target_id(db, "bus_service"),
    )
    saved = client.post(COMPLAINTS, json=body).json()
    forwarded = client.post(f"{COMPLAINTS}/{saved['id']}/forward")
    assert forwarded.status_code == 200, forwarded.text
    assert forwarded.json()["duty"]["driver_name"] == "Saman Kumara"
    assert client.put(f"{COMPLAINTS}/{saved['id']}", json=body).status_code == 409  # locked, so the record is too
    assert snapshot_of(db, saved["id"]).trip_id == trip["id"]


def test_the_trip_reference_is_for_level_one_only(client, db, world, complaint_lists):
    trip = publish_trip(world)
    assert world.admin.post(COMPLAINTS, json=complaint_body(trip["id"])).status_code == 403
    assert TestClient(app).post(COMPLAINTS, json=complaint_body(trip["id"])).status_code == 401

# ---------------------------------------------------------------- what the lookup says when there is no trip


def test_the_lookup_tells_a_bus_that_did_not_operate_from_one_with_no_record(client, db, world):
    from app.models import BusNonOperation

    db.add(BusNonOperation(vehicle_id=world.bus.id, start_date=DAY, end_date=DAY, reason="maintenance"))
    db.commit()
    stopped = search(client).json()
    assert stopped["trips"] == [] and stopped["operation_status"] == "did_not_operate"
    assert stopped["non_operation_reason"] == "maintenance"
    nothing = search(client, on=DAY - timedelta(days=3)).json()
    assert nothing["operation_status"] == "no_record" and nothing["non_operation_reason"] is None
    assert search(client, bus="ZZ-0000").status_code == 404  # an invalid bus number


def test_a_cancelled_trip_is_listed_as_cancelled_and_is_not_a_completed_one(client, db, world):
    trip = publish_trip(world)
    row = db.get(DailyTrip, trip["id"])
    row.trip_status = "cancelled"
    db.commit()
    found = search(client).json()
    assert found["operation_status"] == "cancelled"
    assert [(t["id"], t["trip_status"]) for t in found["trips"]] == [(trip["id"], "cancelled")]
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").json()["trip_status"] == "cancelled"


def test_simulated_records_are_marked_as_such(client, db, world):
    from app.models import SyntheticBatch

    batch = SyntheticBatch(name="t", scale="small", seed=1, config={})
    db.add(batch)
    db.flush()
    trip = publish_trip(world)
    db.get(DailyTrip, trip["id"]).synthetic_batch_id = batch.id
    db.commit()
    assert search(client).json()["trips"][0]["synthetic"] is True
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").json()["synthetic"] is True


def test_the_owner_on_the_published_daily_record_is_shown_when_there_is_no_ownership_record(client, db, world):
    other_owner = Person(full_name="Kamal Silva", person_type=PersonType.OWNER)
    db.add(other_owner)
    db.commit()
    trip = publish_trip(world)
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").json()["owner"]["source"] == "vehicle_record"  # none on the record yet
    db.get(DailyTrip, trip["id"]).owner_person_id = other_owner.id
    db.commit()
    owner = client.get(f"{LOOKUP}/trips/{trip['id']}").json()["owner"]
    assert owner == {"person_id": other_owner.id, "name": "Kamal Silva", "source": "daily_record"}

    # An approved ownership record for that date still comes first.
    created = world.admin.post(
        f"{ADMIN}/owner-assignments",
        json={"vehicle_number": "ND-7782", "owner_person_id": world.owner.id, "valid_from": (DAY - timedelta(days=5)).isoformat()},
    ).json()
    assert world.admin.post(f"{ADMIN}/owner-assignments/{created['id']}/approve").status_code == 200
    assert world.admin.post(f"{ADMIN}/owner-assignments/{created['id']}/publish").status_code == 200
    assert client.get(f"{LOOKUP}/trips/{trip['id']}").json()["owner"]["source"] == "assignment"
