"""The Selected Bus Details feature: safe retries, all-or-nothing saves and what Level 1 may not do."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.roles import UserRole
from app.main import app
from datetime import timedelta

from app.models import (
    AuditLog,
    BusNonOperation,
    Complaint,
    ComplaintDutySnapshot,
    DailyTrip,
    OwnerAssignment,
    Permit,
    Vehicle,
)
from app.services import audit_service
from tests.conftest import make_user, sign_in, target_id
from tests.test_bus_lookup import (  # noqa: F401  (the fixtures and helpers of the lookup tests)
    ADMIN,
    COMPLAINTS,
    DAY,
    LOOKUP,
    complaint_body,
    complaint_lists,
    error_code,
    publish_trip,
    world,
)

KEY = "8f14e45f-ceea-467a-9575-5e1b0f1e0a11"


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


# ---------------------------------------------------------------- safe retries


def test_sending_the_same_new_complaint_twice_creates_it_once(client, db, world, complaint_lists):
    trip = publish_trip(world)
    body = complaint_body(trip["id"], client_request_id=KEY)

    first = client.post(COMPLAINTS, json=body)
    again = client.post(COMPLAINTS, json=body)  # a retry after a lost response, or a double click

    assert first.status_code == 201 and again.status_code == 201
    assert again.json()["id"] == first.json()["id"] and again.json()["trip_id"] == trip["id"]
    assert count(db, Complaint) == 1 and count(db, ComplaintDutySnapshot) == 1
    created = db.scalars(select(AuditLog).where(AuditLog.action == "complaint.create")).all()
    assert len(created) == 1  # and one entry in the audit trail


def test_a_different_key_or_a_different_officer_makes_a_new_complaint(client, db, world, complaint_lists):
    first = client.post(COMPLAINTS, json=complaint_body(None, client_request_id=KEY)).json()
    second = client.post(COMPLAINTS, json=complaint_body(None, client_request_id=KEY + "-2")).json()
    assert first["id"] != second["id"]

    make_user(db, "second@sprpta.test", UserRole.L1, full_name="Second Officer")
    other = TestClient(app)
    sign_in(other, "second@sprpta.test")
    theirs = other.post(COMPLAINTS, json=complaint_body(None, client_request_id=KEY)).json()
    assert theirs["id"] not in (first["id"], second["id"])  # the same key from someone else is not a retry
    assert count(db, Complaint) == 3
    assert client.post(COMPLAINTS, json=complaint_body(None)).status_code == 201  # no key: nothing to match
    assert client.post(COMPLAINTS, json=complaint_body(None, client_request_id="x")).status_code == 422  # too short


def test_the_key_is_ignored_when_a_saved_complaint_is_changed(client, db, world, complaint_lists):
    saved = client.post(COMPLAINTS, json=complaint_body(None, client_request_id=KEY)).json()
    changed = client.put(f"{COMPLAINTS}/{saved['id']}", json={"subject": "Changed", "client_request_id": "another-key-1"})
    assert changed.status_code == 200 and changed.json()["subject"] == "Changed"
    assert count(db, Complaint) == 1


# ---------------------------------------------------------------- all or nothing


def test_a_failed_save_leaves_nothing_behind_and_a_retry_still_works(client, db, world, complaint_lists, monkeypatch):
    trip = publish_trip(world)
    body = complaint_body(trip["id"], client_request_id=KEY)

    real = audit_service.record

    def broken(*args, **kwargs):
        if kwargs.get("action") == "complaint.create":
            raise RuntimeError("the database went away")
        return real(*args, **kwargs)

    monkeypatch.setattr(audit_service, "record", broken)
    quiet = TestClient(app, raise_server_exceptions=False)
    sign_in(quiet, "office@sprpta.test")
    failed = quiet.post(COMPLAINTS, json=body)
    assert failed.status_code == 500
    # The complaint, its bus snapshot and the audit row of the bus selection were all rolled back together.
    assert count(db, Complaint) == 0 and count(db, ComplaintDutySnapshot) == 0
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "complaint.bus_selected")) == 0

    monkeypatch.setattr(audit_service, "record", real)  # the problem is over: the same save is sent again
    retry = client.post(COMPLAINTS, json=body)
    assert retry.status_code == 201 and retry.json()["duty"]["driver_name"] == "Saman Kumara"
    assert count(db, Complaint) == 1 and count(db, ComplaintDutySnapshot) == 1


def test_a_refused_form_with_a_trip_saves_no_complaint(client, db, world, complaint_lists):
    trip = publish_trip(world)
    refused = client.post(COMPLAINTS, json=complaint_body(trip["id"], mobile="not a number", client_request_id=KEY))
    assert refused.status_code == 422 and error_code(refused) == "invalid_mobile"
    assert count(db, Complaint) == 0 and count(db, ComplaintDutySnapshot) == 0
    fixed = client.post(COMPLAINTS, json=complaint_body(trip["id"], mobile="0771234567", client_request_id=KEY))
    assert fixed.status_code == 201 and count(db, Complaint) == 1  # the refused key was not used up


# ---------------------------------------------------------------- what Level 1 may not do


def test_level_one_has_no_way_to_change_bus_permit_owner_or_duty_records(client, db, world):
    trip = publish_trip(world)
    before = (
        db.scalar(select(Vehicle.registered_area_id).where(Vehicle.id == world.bus.id)),
        db.scalar(select(Permit.permit_number).where(Permit.id == world.permit.id)),
        db.scalar(select(DailyTrip.status).where(DailyTrip.id == trip["id"])),
    )
    for path in (f"{LOOKUP}/trips", f"{LOOKUP}/trips/{trip['id']}"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(path).status_code == 405, (method, path)

    owner = {"vehicle_number": "ND-7782", "owner_person_id": world.owner.id, "valid_from": "2026-01-01"}
    admin_paths = [
        ("get", f"{ADMIN}/trips"),
        ("post", f"{ADMIN}/trips"),
        ("post", f"{ADMIN}/trips/{trip['id']}/approve"),
        ("post", f"{ADMIN}/trips/{trip['id']}/publish"),
        ("post", f"{ADMIN}/owner-assignments"),
        ("post", f"{ADMIN}/owner-assignments/1/approve"),
        ("post", f"{ADMIN}/owner-assignments/1/publish"),
    ]
    for method, path in admin_paths:
        sent = getattr(client, method)(path, **({"json": owner} if method == "post" and path.endswith("assignments") else {}))
        assert sent.status_code == 403, (method, path)  # refused by the API, not only hidden in the screen

    db.expire_all()
    assert before == (
        db.scalar(select(Vehicle.registered_area_id).where(Vehicle.id == world.bus.id)),
        db.scalar(select(Permit.permit_number).where(Permit.id == world.permit.id)),
        db.scalar(select(DailyTrip.status).where(DailyTrip.id == trip["id"])),
    )
    assert count(db, OwnerAssignment) == 0


def test_a_forwarded_complaint_and_its_bus_snapshot_cannot_be_changed_by_level_one(client, db, world, complaint_lists):
    from app.models import ComplaintCategory, ComplaintMedium, Severity

    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    trip = publish_trip(world)
    medium, category, severity = (db.scalar(select(m)) for m in (ComplaintMedium, ComplaintCategory, Severity))
    body = complaint_body(
        trip["id"], medium_id=medium.id, category_id=category.id, severity_id=severity.id,
        complainant_name="Kamala", description="Asked for double the fare", target_type_id=target_id(db, "bus_service"),
    )
    saved = client.post(COMPLAINTS, json=body).json()
    assert client.post(f"{COMPLAINTS}/{saved['id']}/forward").status_code == 200

    other_trip = publish_trip(world, vehicle_number="ND-7980", departure_time="09:00")
    refused = client.put(f"{COMPLAINTS}/{saved['id']}", json=complaint_body(other_trip["id"]))
    assert refused.status_code == 409 and error_code(refused) == "not_editable"
    shown = client.get(f"{COMPLAINTS}/{saved['id']}").json()
    assert shown["duty"]["bus_number"] == "ND-7782" and shown["trip_id"] == trip["id"]  # still readable, unchanged


def test_only_level_one_can_read_a_saved_complaints_bus_details(client, db, world, complaint_lists):
    trip = publish_trip(world)
    saved = client.post(COMPLAINTS, json=complaint_body(trip["id"])).json()
    assert world.admin.get(f"{COMPLAINTS}/{saved['id']}").status_code == 403
    assert TestClient(app).get(f"{COMPLAINTS}/{saved['id']}").status_code == 401


# ---------------------------------------------------------------- what the officer typed, and what checking found


def test_a_wrong_number_typed_before_choosing_the_trip_is_kept_and_flagged_as_corrected(client, db, world, complaint_lists):
    trip = publish_trip(world)
    body = complaint_body(trip["id"], vehicle_number="ND-7783")  # one digit off: no such bus on record
    saved = client.post(COMPLAINTS, json=body)
    assert saved.status_code == 201, saved.text
    out = saved.json()
    assert out["vehicle_number"] == "ND-7783"  # the reported number is never silently replaced
    assert out["bus_verification"] == "corrected" and out["trip_id"] == trip["id"]
    row = db.get(Complaint, out["id"])
    assert row.vehicle_id == world.bus.id and row.vehicle_number_entered == "ND-7783"  # the verified bus is stored apart


def test_the_right_number_with_a_trip_is_verified_and_a_different_real_bus_is_refused(client, db, world, complaint_lists):
    trip = publish_trip(world)
    ok = client.post(COMPLAINTS, json=complaint_body(trip["id"], vehicle_number="nd-7782")).json()
    assert ok["bus_verification"] == "verified" and ok["vehicle_number"] == "ND-7782"
    other = client.post(COMPLAINTS, json=complaint_body(trip["id"], vehicle_number="ND-7980"))
    assert other.status_code == 422 and error_code(other) == "trip_mismatch"  # another real bus is a conflict, not a typo


def test_without_a_trip_the_bus_is_unverified_or_not_found(client, db, world, complaint_lists):
    known = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ND-7782")).json()
    assert known["bus_verification"] == "unverified" and known["trip_id"] is None
    unknown = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ZZ-0000")).json()
    assert unknown["bus_verification"] == "not_found" and unknown["vehicle_number"] == "ZZ-0000"
    blank = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number=None)).json()
    assert blank["bus_verification"] is None


def test_the_complainant_type_is_saved_and_only_known_types_are_accepted(client, db, world, complaint_lists):
    saved = client.post(COMPLAINTS, json=complaint_body(None, complainant_type="conductor")).json()
    assert saved["complainant_type"] == "conductor"
    assert client.get(f"{COMPLAINTS}/{saved['id']}").json()["complainant_type"] == "conductor"
    assert client.post(COMPLAINTS, json=complaint_body(None, complainant_type="alien")).status_code == 422
    assert client.post(COMPLAINTS, json=complaint_body(None)).json()["complainant_type"] is None


# ---------------------------------------------------------------- what checking the bus found


def test_the_same_bus_typed_in_another_format_is_verified_not_corrected(client, db, world, complaint_lists):
    trip = publish_trip(world)
    for typed in ("nd 7782", "ND7782", "nd-7782", " ND-7782 "):
        saved = client.post(COMPLAINTS, json=complaint_body(trip["id"], vehicle_number=typed)).json()
        assert saved["bus_verification"] == "verified", typed
        assert saved["vehicle_number"] == "ND-7782", typed  # the number on record, not the way it was typed


def test_a_cancelled_trip_is_flagged_trip_cancelled(client, db, world, complaint_lists):
    trip = publish_trip(world)
    db.get(DailyTrip, trip["id"]).trip_status = "cancelled"
    db.commit()
    chosen = client.post(COMPLAINTS, json=complaint_body(trip["id"])).json()
    assert chosen["bus_verification"] == "trip_cancelled" and chosen["trip_id"] == trip["id"]
    typed = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ND-7782", complaint_date=DAY.isoformat())).json()
    assert typed["bus_verification"] == "trip_cancelled"  # every published trip of that day was cancelled


def test_a_bus_the_records_say_did_not_operate_is_flagged_not_operated(client, db, world, complaint_lists):
    db.add(BusNonOperation(vehicle_id=world.bus.id, start_date=DAY, end_date=DAY, reason="maintenance"))
    db.commit()
    stopped = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ND-7782", complaint_date=DAY.isoformat())).json()
    assert stopped["bus_verification"] == "not_operated"
    other_day = (DAY - timedelta(days=3)).isoformat()
    ran = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ND-7782", complaint_date=other_day)).json()
    assert ran["bus_verification"] == "unverified"  # no record either way: nothing is assumed
    undated = client.post(COMPLAINTS, json=complaint_body(None, vehicle_number="ND-7782")).json()
    assert undated["bus_verification"] == "unverified"
