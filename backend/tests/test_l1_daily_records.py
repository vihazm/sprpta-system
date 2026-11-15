"""Level 1 enters daily bus operation records; they stay Pending Verification until Admin approves and publishes."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.roles import UserRole
from app.main import app
from app.models import AuditLog, DailyTrip, TripDuty
from tests.conftest import make_user, sign_in, target_id
from tests.test_bus_lookup import (  # noqa: F401  (the fixtures and helpers of the lookup tests)
    ADMIN,
    COMPLAINTS,
    DAY,
    LOOKUP,
    TODAY,
    complaint_lists,
    error_code,
    search,
    trip_body,
    world,
)

RECORDS = "/api/l1/daily-records"


def body(w, **changes) -> dict:
    return {
        **trip_body(w),
        "end_time": "08:15",
        "owner_person_id": w.owner.id,
        "driver_start": "06:00",
        "driver_end": "12:00",
        "conductor_start": "06:00",
        "conductor_end": "12:00",
        "remarks": "Entered from the depot sheet",
        **changes,
    }


def add(client, w, **changes) -> dict:
    created = client.post(RECORDS, json=body(w, **changes))
    assert created.status_code == 201, created.text
    return created.json()


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


# ---------------------------------------------------------------- adding a record


def test_level_one_adds_a_record_that_is_pending_verification(client, db, world):
    saved = add(client, world)
    assert saved["id"] and saved["status"] == "draft"
    assert saved["status_label"] == "Pending Verification" and saved["verification_status"] == "Pending Verification"
    assert (saved["vehicle_number"], saved["permit_number"], saved["area_name"]) == ("ND-7782", "002108", "Galle")
    assert (saved["driver_name"], saved["conductor_name"], saved["owner_name"]) == (
        "Saman Kumara", "Chaminda Rathnayake", "Nimal Perera",
    )
    assert (saved["departure_time"], saved["end_time"], saved["driver_start"]) == ("06:30:00", "08:15:00", "06:00:00")
    assert saved["entered_by"] == "Office Staff" and saved["editable"] is True and saved["remarks"]

    row = db.get(DailyTrip, saved["id"])
    assert row.created_by_user_id is not None and row.approved_at is None and row.published_at is None
    duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == row.id))
    assert duty.driver_person_id == world.driver.id and duty.verified_at is None  # nobody is marked verified
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "trip.create")).all()
    assert len(audit) == 1  # saved with its audit row, in one transaction


def test_several_trips_of_one_bus_on_one_day_but_not_the_same_trip_twice(client, db, world):
    add(client, world)
    add(client, world, departure_time="14:00", end_time="16:00")
    duplicate = client.post(RECORDS, json=body(world))
    assert duplicate.status_code == 409 and error_code(duplicate) == "duplicate_trip"
    assert count(db, DailyTrip) == 2 and count(db, TripDuty) == 2  # the refused save left nothing behind


def test_a_record_may_leave_people_out_and_nobody_is_invented(client, db, world):
    saved = add(
        client, world, driver_person_id=None, conductor_person_id=None, owner_person_id=None,
        driver_start=None, driver_end=None, conductor_start=None, conductor_end=None, end_time=None, remarks=None,
    )
    assert saved["driver_name"] is None and saved["conductor_name"] is None and saved["end_time"] is None
    assert count(db, TripDuty) == 0


def test_the_server_checks_everything_again(client, db, world):
    def refused(**changes):
        response = client.post(RECORDS, json=body(world, **changes))
        assert response.status_code in (409, 422), (changes, response.text)
        return response

    assert error_code(refused(service_date=(TODAY + timedelta(days=1)).isoformat())) == "future_date"
    assert error_code(refused(vehicle_number="ZZ-0000")) == "unknown_vehicle"
    assert error_code(refused(driver_person_id=world.conductor.id)) == "unknown_driver"  # wrong kind of person
    assert error_code(refused(conductor_person_id=world.driver.id)) == "unknown_conductor"
    assert error_code(refused(owner_person_id=world.driver.id)) == "unknown_owner"
    assert error_code(refused(route_stand_id=999_999)) == "unknown_route"
    assert error_code(refused(driver_person_id=None)) == "duty_without_person"  # times without a person
    assert refused(origin="   ").status_code == 422
    assert refused(departure_time="not a time").status_code == 422
    assert count(db, DailyTrip) == 0


def test_a_bus_without_a_permit_cannot_have_a_record(client, db, world):
    from app.models import Permit

    db.get(Permit, world.permit.id).vehicle_id = world.other_permit.vehicle_id  # the bus now has no permit of its own
    db.commit()
    assert error_code(client.post(RECORDS, json=body(world))) == "no_permit"


# ---------------------------------------------------------------- my records, reopening and editing


def test_my_daily_bus_records_lists_reopens_and_edits_only_my_pending_records(client, db, world):
    first = add(client, world)
    add(client, world, departure_time="14:00", end_time="16:00")
    listing = client.get(RECORDS).json()
    assert listing["total"] == 2 and [r["departure_time"] for r in listing["items"]] == ["14:00:00", "06:30:00"]
    assert client.get(RECORDS, params={"search": "7782"}).json()["total"] == 2
    assert client.get(RECORDS, params={"search": "nothing"}).json()["total"] == 0
    assert client.get(RECORDS, params={"service_date": DAY.isoformat(), "status": "draft"}).json()["total"] == 2
    assert client.get(RECORDS, params={"status": "published"}).json()["total"] == 0

    reopened = client.get(f"{RECORDS}/{first['id']}").json()
    assert reopened["id"] == first["id"] and reopened["status_label"] == "Pending Verification"

    changed = client.put(f"{RECORDS}/{first['id']}", json=body(world, remarks="Corrected", driver_person_id=None,
                                                               driver_start=None, driver_end=None))
    assert changed.status_code == 200 and changed.json()["remarks"] == "Corrected"
    assert changed.json()["driver_name"] is None and changed.json()["conductor_name"] == "Chaminda Rathnayake"
    clash = client.put(f"{RECORDS}/{first['id']}", json=body(world, departure_time="14:00"))
    assert clash.status_code == 409 and error_code(clash) == "duplicate_trip"
    assert count(db, DailyTrip) == 2
    assert db.scalars(select(AuditLog).where(AuditLog.action == "trip.update")).all()


def test_another_officer_cannot_see_or_change_my_record(client, db, world):
    mine = add(client, world)
    make_user(db, "second@sprpta.test", UserRole.L1, full_name="Second Officer")
    other = TestClient(app)
    sign_in(other, "second@sprpta.test")
    assert other.get(RECORDS).json()["total"] == 0
    assert other.get(f"{RECORDS}/{mine['id']}").status_code == 404
    assert other.put(f"{RECORDS}/{mine['id']}", json=body(world, remarks="Hijacked")).status_code == 404
    assert client.get(f"{RECORDS}/{mine['id']}").json()["remarks"] == "Entered from the depot sheet"


# ---------------------------------------------------------------- what Level 1 may not do


def test_pending_records_are_not_published_and_level_one_cannot_publish(client, db, world):
    saved = add(client, world)
    assert search(client).json()["trips"] == []  # the lookup shows published records only
    assert client.get(f"{LOOKUP}/trips/{saved['id']}").status_code == 404
    for step in ("approve", "publish"):
        assert client.post(f"{ADMIN}/trips/{saved['id']}/{step}").status_code == 403
    db.expire_all()
    assert db.get(DailyTrip, saved["id"]).status.value == "draft"


def test_only_level_one_staff_use_these_routes(client, db, world):
    saved = add(client, world)
    assert world.admin.get(RECORDS).status_code == 403
    assert world.admin.post(RECORDS, json=body(world)).status_code == 403
    assert world.admin.get(f"{RECORDS}/{saved['id']}").status_code == 403
    anonymous = TestClient(app)
    assert anonymous.get(RECORDS).status_code == 401
    assert anonymous.post(RECORDS, json=body(world)).status_code == 401
    make_user(db, "chair@sprpta.test", UserRole.L3)
    area = TestClient(app)
    sign_in(area, "chair@sprpta.test")
    assert area.get(RECORDS).status_code == 403


# ---------------------------------------------------------------- the whole flow


def test_entered_approved_published_searched_and_used_in_a_classified_complaint(client, db, world, complaint_lists):
    from app.models import ComplaintCategory, ComplaintMedium, Severity

    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    saved = add(client, world)

    # Admin verifies and publishes it through the existing admin routes.
    approved = world.admin.post(f"{ADMIN}/trips/{saved['id']}/approve")
    assert approved.status_code == 200 and approved.json()["duty_verified"] is True
    assert client.get(RECORDS, params={"status": "approved"}).json()["items"][0]["verification_status"] == "Verified"
    assert world.admin.post(f"{ADMIN}/trips/{saved['id']}/publish").status_code == 200
    mine = client.get(f"{RECORDS}/{saved['id']}").json()
    assert (mine["status_label"], mine["editable"]) == ("Published", False)
    refused = client.put(f"{RECORDS}/{saved['id']}", json=body(world, remarks="Late change"))
    assert refused.status_code == 409 and error_code(refused) == "not_editable"

    # Now the lookup finds it, with the verified driver and conductor.
    found = search(client).json()["trips"]
    assert [t["id"] for t in found] == [saved["id"]]
    details = client.get(f"{LOOKUP}/trips/{saved['id']}").json()
    assert details["verification_status"] == "Verified" and details["driver"]["name"] == "Saman Kumara"

    # A complaint classified against the driver, using the trip.
    complaint = client.post(COMPLAINTS, json={
        "trip_id": saved["id"], "target_type_id": target_id(db, "driver"),
        "subject_person_id": world.driver.id, "subject": "Rude driver", "medium_id": db.scalar(select(ComplaintMedium.id)),
        "complaint_date": DAY.isoformat(), "category_id": db.scalar(select(ComplaintCategory.id)),
        "severity_id": db.scalar(select(Severity.id)), "complainant_name": "Kamala", "description": "Shouted at me",
        "route_stand_id": world.route.id,
    })
    assert complaint.status_code == 201, complaint.text
    assert complaint.json()["accused_status"] == "verified_duty" and complaint.json()["trip_id"] == saved["id"]
    assert client.post(f"{COMPLAINTS}/{complaint.json()['id']}/forward").status_code == 200

    mine_list = client.get(COMPLAINTS, params={"target": "driver"}).json()
    assert mine_list["total"] == 1 and mine_list["items"][0]["accused_name"] == "Saman Kumara"
    assert client.get("/api/l1/dashboard").json()["by_target"]["driver"] == 1


# ---------------------------------------------------------------- the synthetic history script


def test_the_history_script_is_deterministic_repeatable_labelled_and_removable(client, db, world, complaint_lists, monkeypatch):
    from app.models import Area, Complaint, Person, Vehicle
    from app.scripts import seed_dev_history as seed

    monkeypatch.setattr(seed, "check_environment", lambda: None)
    monkeypatch.setattr(seed, "START", DAY - timedelta(days=8))
    monkeypatch.setattr(seed, "END", DAY)
    monkeypatch.setattr(seed, "RECENT", DAY - timedelta(days=2))
    monkeypatch.setattr(seed, "COMPLAINTS", 10)
    for name in ("Matara", "Hambantota"):
        db.add(Area(name=name))
    db.commit()

    first = seed.plan_trips()
    assert [(t.day, t.bus, t.slot, t.status) for t in first] == [(t.day, t.bus, t.slot, t.status) for t in seed.plan_trips()]
    seed.create(db, first, seed.plan_complaints(first))
    trips = db.scalar(select(func.count()).select_from(DailyTrip).join(Vehicle, Vehicle.id == DailyTrip.vehicle_id)
                      .where(Vehicle.vehicle_number.like("SP SY-%")))
    assert trips == len(first)
    everything = db.scalar(select(func.count()).select_from(DailyTrip))
    assert everything > len(first)  # the other buses in the database got test trips too
    other = db.scalars(select(DailyTrip).join(Vehicle, Vehicle.id == DailyTrip.vehicle_id).where(Vehicle.vehicle_number == "ND-7782")).all()
    assert other and all(x.remarks == "Synthetic test data" for x in other)
    statuses = {t.status.value for t in db.scalars(select(DailyTrip).where(DailyTrip.remarks == "Synthetic test data"))}
    assert statuses >= {"published"}
    assert all(p.team_label == "SYNTHETIC-TEST-DATA" for p in db.scalars(select(Person).where(Person.full_name.like("Synthetic %"))))
    syn = db.scalars(select(Complaint).where(Complaint.client_request_id.like("syn-hist-%"))).all()
    assert syn and all(c.subject.startswith("[SYNTHETIC]") for c in syn)

    seed.create(db, first, seed.plan_complaints(first))  # a second run adds nothing
    assert db.scalar(select(func.count()).select_from(DailyTrip)) == everything
    assert len(db.scalars(select(Complaint).where(Complaint.client_request_id.like("syn-hist-%"))).all()) == len(syn)

    published = next(t for t in first if t.status == "published")
    found = search(client, bus=f"SP SY-{published.bus + 1:04d}", on=published.day).json()["trips"]
    assert found  # the lookup finds the synthetic published trips

    seed.remove(db)
    assert db.scalar(select(func.count()).select_from(DailyTrip)) == 0
    assert db.scalars(select(Vehicle).where(Vehicle.vehicle_number.like("SP SY-%"))).all() == []
