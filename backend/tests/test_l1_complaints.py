from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import ComplaintStatus, PersonType, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import (
    Area,
    AuditLog,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintMedium,
    Permit,
    Person,
    RouteStand,
    Severity,
    Vehicle,
)
from app.core.enums import PlaceKind
from tests.conftest import make_user, sign_in

URL = "/api/l1/complaints"
TODAY = datetime.now(LOCAL).date().isoformat()
YEAR = datetime.now(LOCAL).year


class Lists:
    """The master data the form depends on, and the signed-in L1 user."""


@pytest.fixture
def lists(db, client, galle, tmp_path, monkeypatch) -> Lists:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    data = Lists()
    data.area = galle
    data.officer = make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=galle.id, full_name="Ruwan Silva")
    data.l1 = make_user(db, "office@sprpta.test", UserRole.L1, full_name="Office Staff")
    data.medium = ComplaintMedium(name="WhatsApp")
    data.portal = ComplaintMedium(name="Portal", is_system=True)
    data.category = ComplaintCategory(name="Overcharging")
    data.severity = Severity(
        name="High", rank=2, forward_days=1, decide_days=3, close_days=7, rating_weight=4
    )
    owner = Person(full_name="Nimal Perera", person_type=PersonType.OWNER)
    data.route = RouteStand(kind=PlaceKind.ROUTE, name="Galle - Matara", area_id=galle.id)
    db.add_all([data.medium, data.portal, data.category, data.severity, data.route, owner])
    db.flush()
    data.vehicle = Vehicle(
        vehicle_number="SP NB-2345", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, owner_person_id=owner.id
    )
    db.add(data.vehicle)
    db.flush()
    db.add(Permit(permit_number="GL-BP-0101", vehicle_id=data.vehicle.id, holder_person_id=owner.id))
    db.commit()
    sign_in(client, "office@sprpta.test")
    return data


def form(lists: Lists, **changes) -> dict:
    """A complete form, ready to forward."""
    body = {
        "medium_id": lists.medium.id,
        "is_anonymous": False,
        "complainant_name": "Kamala Fernando",
        "contact": "0771234567",
        "complaint_date": TODAY,
        "vehicle_number": "sp nb-2345",
        "route_stand_id": lists.route.id,
        "category_id": lists.category.id,
        "severity_id": lists.severity.id,
        "subject": "Charged more than the fare",
        "description": "The conductor asked for double the fare.",
    }
    return {**body, **changes}


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def new_draft(client, lists, **changes) -> dict:
    response = client.post(URL, json=form(lists, **changes))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------- access


def test_only_level_one_staff_may_use_the_complaint_api(client, db, lists):
    client.post("/api/auth/logout")
    assert client.get(f"{URL}/options").status_code == 401
    make_user(db, "admin@sprpta.test", UserRole.ADMIN)
    sign_in(client, "admin@sprpta.test")
    assert client.get(f"{URL}/options").status_code == 403
    assert client.post(URL, json={}).status_code == 403


# ---------------------------------------------------------------- lookups


def test_options_list_the_form_choices_without_the_portal_medium(client, lists):
    options = client.get(f"{URL}/options").json()
    assert [m["name"] for m in options["mediums"]] == ["WhatsApp"]
    assert options["categories"][0]["name"] == "Overcharging"
    assert options["severities"][0] == {"id": lists.severity.id, "name": "High", "forward_days": 1}


def test_vehicle_lookup_ignores_case_spaces_and_hyphens_and_fills_in_the_record(client, lists):
    for typed in ("spnb-2345", "SP NB 2345", "sp-nb-2345", "SPNB2345"):
        assert client.get(f"{URL}/lookup/vehicle", params={"number": typed}).status_code == 200, typed
    found = client.get(f"{URL}/lookup/vehicle", params={"number": "spnb-2345"})
    assert found.status_code == 200
    assert found.json() | {"id": 0} == {
        "id": 0,
        "vehicle_number": "SP NB-2345",
        "vehicle_type": "bus",
        "area_id": lists.area.id,
        "area_name": "Galle",
        "permit_number": "GL-BP-0101",
        "owner_name": "Nimal Perera",
        "past_complaints": 0,
    }
    missing = client.get(f"{URL}/lookup/vehicle", params={"number": "XX 0000"})
    assert missing.status_code == 404 and error_code(missing) == "vehicle_not_found"


def test_people_search_filters_by_name_and_type(client, db, lists):
    db.add(Person(full_name="Saman Kumara", person_type=PersonType.DRIVER))
    db.add(Person(full_name="Saman Perera", person_type=PersonType.CONDUCTOR))
    db.commit()
    found = client.get(f"{URL}/lookup/people", params={"search": "saman", "person_type": "driver"}).json()
    assert [p["full_name"] for p in found] == ["Saman Kumara"]
    assert client.get(f"{URL}/lookup/people").json() == []


# ---------------------------------------------------------------- saving the form


def test_a_draft_takes_its_permit_owner_and_area_from_the_vehicle(client, db, lists):
    draft = new_draft(client, lists)
    assert draft["status"] == "draft"
    assert draft["reference_number"] is None
    assert draft["contact"] == "+94771234567"
    assert draft["vehicle"]["permit_number"] == "GL-BP-0101"
    assert draft["area_name"] == "Galle"
    row = db.get(Complaint, draft["id"])
    assert row.vehicle_id == lists.vehicle.id and row.owner_person_id is not None and row.permit_id is not None
    assert row.entered_by_user_id == lists.l1.id
    audit = db.scalars(select(AuditLog).where(AuditLog.complaint_id == row.id)).one()
    assert (audit.action, audit.to_status, audit.actor_role) == ("complaint.create", ComplaintStatus.DRAFT, "l1")


def test_the_person_the_complaint_is_about_is_returned_by_name(client, db, lists):
    driver = Person(full_name="Saman Kumara", person_type=PersonType.DRIVER)
    db.add(driver)
    db.commit()
    linked = new_draft(client, lists, subject_person_id=driver.id, subject_person_text="ignored")
    assert linked["subject_person_name"] == "Saman Kumara"
    typed = new_draft(client, lists, subject_person_text="  Unknown conductor ")
    assert typed["subject_person_name"] == "Unknown conductor"


def test_a_draft_can_be_saved_half_empty_and_an_unknown_vehicle_is_kept_as_typed(client, lists):
    empty = client.post(URL, json={})
    assert empty.status_code == 201
    typed = new_draft(client, lists, vehicle_number="XX 0000")
    assert typed["vehicle_number"] == "XX 0000" and typed["vehicle"] is None and typed["area_id"] is None


def test_an_anonymous_complaint_keeps_no_name_and_no_contact(client, lists):
    draft = new_draft(client, lists, is_anonymous=True)
    assert draft["complainant_name"] is None and draft["contact"] is None


def test_the_form_is_checked(client, lists):
    cases = {
        "invalid_contact": {"contact": "not a contact"},
        "future_date": {"complaint_date": (date.today() + timedelta(days=2)).isoformat()},
        "unknown_medium": {"medium_id": 9999},
        "unknown_category": {"category_id": 9999},
        "unknown_severity": {"severity_id": 9999},
        "unknown_person": {"subject_person_id": 9999},
        "unknown_route_stand": {"route_stand_id": 9999},
    }
    for code, change in cases.items():
        response = client.post(URL, json=form(lists, **change))
        assert response.status_code == 422 and error_code(response) == code, code
    # Portal is the portal's own medium, not one L1 can choose.
    assert error_code(client.post(URL, json=form(lists, medium_id=lists.portal.id))) == "unknown_medium"
    assert client.post(URL, json={"subject": "x" * 201}).status_code == 422


def test_a_saved_form_can_be_changed_and_read_back(client, lists):
    draft = new_draft(client, lists)
    changed = client.put(f"{URL}/{draft['id']}", json=form(lists, subject="Rude conductor"))
    assert changed.status_code == 200 and changed.json()["subject"] == "Rude conductor"
    assert client.get(f"{URL}/{draft['id']}").json()["subject"] == "Rude conductor"
    assert client.get(f"{URL}/999999").status_code == 404
    assert client.put(f"{URL}/999999", json={}).status_code == 404


def test_open_complaints_are_listed_to_finish_later(client, lists):
    draft = new_draft(client, lists)
    incomplete = new_draft(client, lists, subject="Second")
    client.post(f"{URL}/{incomplete['id']}/incomplete")
    forwarded = new_draft(client, lists, subject="Third")
    client.put(f"{URL}/{forwarded['id']}/duplicates/{incomplete['id']}", json={"link_type": "not_duplicate"})
    assert client.post(f"{URL}/{forwarded['id']}/forward").status_code == 200

    everything = client.get(URL).json()
    assert {c["id"] for c in everything} == {draft["id"], incomplete["id"]}
    only_incomplete = client.get(URL, params={"status": "incomplete"}).json()
    assert [c["id"] for c in only_incomplete] == [incomplete["id"]]


# ---------------------------------------------------------------- incomplete and forward


def test_saving_as_incomplete_issues_the_reference_number_and_pauses_the_clock(client, db, lists):
    draft = new_draft(client, lists)
    saved = client.post(f"{URL}/{draft['id']}/incomplete").json()
    assert saved["status"] == "incomplete"
    assert saved["reference_number"] == f"SPRPTA-{YEAR}-{draft['id']:06d}"
    row = db.get(Complaint, draft["id"])
    assert row.registered_at is not None and row.paused_since is not None
    assert error_code(client.post(f"{URL}/{draft['id']}/incomplete")) == "already_incomplete"


def test_forwarding_goes_to_the_area_officer_and_issues_the_reference_number(client, db, lists):
    draft = new_draft(client, lists)
    sent = client.post(f"{URL}/{draft['id']}/forward")
    assert sent.status_code == 200
    body = sent.json()
    assert body["status"] == "forwarded"
    assert body["reference_number"].startswith(f"SPRPTA-{YEAR}-")
    assert body["assigned_l2_name"] == "Ruwan Silva" and body["forwarded_at"] is not None

    row = db.get(Complaint, draft["id"])
    assert row.assigned_l2_user_id == lists.officer.id and row.registered_at is not None
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "complaint.forward")).one()
    assert (audit.from_status, audit.to_status) == (ComplaintStatus.DRAFT, ComplaintStatus.FORWARDED)
    assert audit.details == {"assigned_l2_user_id": lists.officer.id}


def test_finishing_an_incomplete_complaint_resumes_the_clock_and_keeps_its_number(client, db, lists):
    draft = new_draft(client, lists, subject=None)
    incomplete = client.post(f"{URL}/{draft['id']}/incomplete").json()
    assert error_code(client.post(f"{URL}/{draft['id']}/forward")) == "missing_details"

    client.put(f"{URL}/{draft['id']}", json=form(lists))
    sent = client.post(f"{URL}/{draft['id']}/forward").json()
    assert sent["status"] == "forwarded" and sent["reference_number"] == incomplete["reference_number"]
    assert sent["registered_at"] == incomplete["registered_at"]  # the clock started at the first registration
    row = db.get(Complaint, draft["id"])
    assert row.paused_since is None and row.paused_total > timedelta(0)


def test_forwarding_names_everything_that_is_missing(client, lists):
    draft = new_draft(
        client, lists, subject=None, description=" ", vehicle_number="XX 0000", complainant_name=None, route_stand_id=None
    )
    response = client.post(f"{URL}/{draft['id']}/forward")
    assert response.status_code == 422 and error_code(response) == "missing_details"
    message = response.json()["detail"]["message"]
    for needed in ("a vehicle that is on record", "route or stand", "subject", "description", "complainant name"):
        assert needed in message
    assert "medium" not in message


def test_an_anonymous_complaint_does_not_need_a_name_to_be_forwarded(client, lists):
    draft = new_draft(client, lists, is_anonymous=True)
    assert client.post(f"{URL}/{draft['id']}/forward").status_code == 200


def test_forwarding_needs_an_active_officer_for_the_area(client, db, lists):
    lists.officer.is_active = False
    db.commit()
    draft = new_draft(client, lists)
    response = client.post(f"{URL}/{draft['id']}/forward")
    assert response.status_code == 409 and error_code(response) == "no_officer"
    assert db.get(Complaint, draft["id"]).status == ComplaintStatus.DRAFT


def test_a_forwarded_complaint_can_no_longer_be_changed(client, lists):
    draft = new_draft(client, lists)
    client.post(f"{URL}/{draft['id']}/forward")
    uri = f"{URL}/{draft['id']}"
    attempts = [
        client.put(uri, json=form(lists)),
        client.post(f"{uri}/forward"),
        client.post(f"{uri}/incomplete"),
        client.post(f"{uri}/reject", json={"rejection_type": "spam", "reason": "Spam"}),
        client.post(f"{uri}/attachments", files={"file": ("a.pdf", b"x", "application/pdf")}),
    ]
    for response in attempts:
        assert response.status_code == 409 and error_code(response) == "not_editable"


# ---------------------------------------------------------------- reject


def test_rejecting_needs_a_reason_and_is_final(client, db, lists):
    draft = new_draft(client, lists)
    uri = f"{URL}/{draft['id']}/reject"
    assert client.post(uri, json={"rejection_type": "spam", "reason": "   "}).status_code == 422
    assert client.post(uri, json={"rejection_type": "spam"}).status_code == 422

    rejected = client.post(uri, json={"rejection_type": "out_of_jurisdiction", "reason": "A train, not covered"})
    assert rejected.status_code == 200
    body = rejected.json()
    assert (body["status"], body["rejection_type"]) == ("rejected", "out_of_jurisdiction")
    assert body["rejection_reason"] == "A train, not covered" and body["rejected_at"] is not None
    assert body["reference_number"] is None  # a draft that was never registered stays without one

    audit = db.scalars(select(AuditLog).where(AuditLog.action == "complaint.reject")).one()
    assert audit.reason == "A train, not covered"
    assert client.post(f"{URL}/{draft['id']}/forward").status_code == 409


def test_a_duplicate_is_rejected_with_the_earlier_case(client, db, lists):
    earlier = new_draft(client, lists)
    earlier_ref = client.post(f"{URL}/{earlier['id']}/forward").json()["reference_number"]
    draft = new_draft(client, lists)
    uri = f"{URL}/{draft['id']}/reject"

    no_case = client.post(uri, json={"rejection_type": "duplicate", "reason": "Same incident"})
    assert no_case.status_code == 422 and error_code(no_case) == "unknown_duplicate"
    unknown = client.post(uri, json={"rejection_type": "duplicate", "reason": "Same", "duplicate_of_reference": "NOPE"})
    assert error_code(unknown) == "unknown_duplicate"

    rejected = client.post(
        uri, json={"rejection_type": "duplicate", "reason": "Same incident", "duplicate_of_reference": earlier_ref}
    ).json()
    assert rejected["status"] == "rejected" and rejected["duplicate_of_reference"] == earlier_ref
    row = db.get(Complaint, draft["id"])
    assert row.duplicate_of_complaint_id == earlier["id"]


def test_rejecting_a_marked_duplicate_does_not_log_the_same_choice_twice(client, db, lists):
    earlier = new_draft(client, lists)
    earlier = client.post(f"{URL}/{earlier['id']}/forward").json()
    draft = new_draft(client, lists)
    client.put(f"{URL}/{draft['id']}/duplicates/{earlier['id']}", json={"link_type": "duplicate_of"})
    rejected = client.post(
        f"{URL}/{draft['id']}/reject",
        json={"rejection_type": "duplicate", "reason": "Same", "duplicate_of_reference": earlier["reference_number"]},
    )
    assert rejected.status_code == 200
    choices = db.scalars(select(AuditLog).where(AuditLog.action == "duplicate.decide")).all()
    assert len(choices) == 1


# ---------------------------------------------------------------- duplicate check


def test_possible_duplicates_are_the_earlier_cases_on_the_same_vehicle(client, db, lists):
    earlier = new_draft(client, lists, subject="Charged more than the fare")
    earlier = client.post(f"{URL}/{earlier['id']}/forward").json()
    other_vehicle = Vehicle(
        vehicle_number="SP NB-9999", vehicle_type=VehicleType.BUS, registered_area_id=lists.area.id
    )
    db.add(other_vehicle)
    db.commit()
    elsewhere = new_draft(client, lists, vehicle_number="SP NB-9999")
    client.post(f"{URL}/{elsewhere['id']}/incomplete")
    draft = new_draft(client, lists, subject="Charged more than the fare")

    found = client.get(f"{URL}/{draft['id']}/duplicates").json()
    assert [c["reference_number"] for c in found] == [earlier["reference_number"]]
    assert found[0]["match"] == 100 and found[0]["link_type"] is None
    assert client.get(f"{URL}/999999/duplicates").status_code == 404


def test_a_draft_without_a_vehicle_has_no_possible_duplicates(client, lists):
    draft = new_draft(client, lists, vehicle_number=None)
    assert client.get(f"{URL}/{draft['id']}/duplicates").json() == []


def test_the_duplicate_choice_is_stored_and_can_be_changed(client, db, lists):
    earlier = new_draft(client, lists)
    earlier = client.post(f"{URL}/{earlier['id']}/forward").json()
    draft = new_draft(client, lists)
    uri = f"{URL}/{draft['id']}/duplicates/{earlier['id']}"

    related = client.put(uri, json={"link_type": "related"})
    assert related.status_code == 200 and related.json()[0]["link_type"] == "related"
    changed = client.put(uri, json={"link_type": "not_duplicate"}).json()
    assert changed[0]["link_type"] == "not_duplicate"
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "duplicate.decide").limit(1)) is not None

    assert client.put(f"{URL}/{draft['id']}/duplicates/{draft['id']}", json={"link_type": "related"}).status_code == 404
    assert client.put(f"{URL}/{draft['id']}/duplicates/999999", json={"link_type": "related"}).status_code == 404
    assert client.put(uri, json={"link_type": "merged"}).status_code == 422


def test_every_possible_duplicate_needs_a_choice_before_forwarding(client, lists):
    earlier = new_draft(client, lists)
    earlier = client.post(f"{URL}/{earlier['id']}/forward").json()
    draft = new_draft(client, lists)

    blocked = client.post(f"{URL}/{draft['id']}/forward")
    assert blocked.status_code == 409 and error_code(blocked) == "duplicate_undecided"

    client.put(f"{URL}/{draft['id']}/duplicates/{earlier['id']}", json={"link_type": "not_duplicate"})
    assert client.post(f"{URL}/{draft['id']}/forward").status_code == 200


def test_a_complaint_marked_as_a_duplicate_cannot_be_forwarded(client, lists):
    earlier = new_draft(client, lists)
    earlier = client.post(f"{URL}/{earlier['id']}/forward").json()
    draft = new_draft(client, lists)
    client.put(f"{URL}/{draft['id']}/duplicates/{earlier['id']}", json={"link_type": "duplicate_of"})

    blocked = client.post(f"{URL}/{draft['id']}/forward")
    assert blocked.status_code == 409 and error_code(blocked) == "marked_duplicate"

    client.put(f"{URL}/{draft['id']}/duplicates/{earlier['id']}", json={"link_type": "related"})
    assert client.post(f"{URL}/{draft['id']}/forward").status_code == 200


# ---------------------------------------------------------------- evidence


def test_evidence_can_be_attached_and_removed_while_the_complaint_is_open(client, db, lists, tmp_path):
    draft = new_draft(client, lists)
    uri = f"{URL}/{draft['id']}/attachments"
    added = client.post(
        uri, files={"file": ("../../original message.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"description": "original message"},
    )
    assert added.status_code == 201
    file = added.json()
    assert file["file_name"] == "original message.pdf" and file["size_bytes"] == 13
    assert file["description"] == "original message"

    stored = db.get(ComplaintAttachment, file["id"])
    assert (tmp_path / stored.storage_path).read_bytes() == b"%PDF-1.4 test"
    assert stored.uploaded_by_user_id == lists.l1.id and stored.storage_path.startswith(f"complaints/{draft['id']}/")
    assert [a["id"] for a in client.get(f"{URL}/{draft['id']}").json()["attachments"]] == [file["id"]]

    assert client.delete(f"{uri}/{file['id']}").status_code == 204
    assert client.get(f"{URL}/{draft['id']}").json()["attachments"] == []
    db.refresh(stored)
    assert stored.removed_at is not None  # soft removal: the row stays
    assert client.delete(f"{uri}/{file['id']}").status_code == 404
    actions = db.scalars(select(AuditLog.action).where(AuditLog.action.like("attachment.%")).order_by(AuditLog.id)).all()
    assert actions == ["attachment.add", "attachment.remove"]


def test_evidence_files_are_checked(client, lists):
    uri = f"{URL}/{new_draft(client, lists)['id']}/attachments"
    wrong_type = client.post(uri, files={"file": ("run.exe", b"MZ", "application/x-msdownload")})
    assert wrong_type.status_code == 415 and error_code(wrong_type) == "file_type_not_allowed"
    empty = client.post(uri, files={"file": ("a.pdf", b"", "application/pdf")})
    assert empty.status_code == 422 and error_code(empty) == "empty_file"
    big = client.post(uri, files={"file": ("a.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")})
    assert big.status_code == 413 and error_code(big) == "file_too_large"
    assert client.post(f"{URL}/999999/attachments", files={"file": ("a.pdf", b"x", "application/pdf")}).status_code == 404


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 8


def test_evidence_contents_must_match_the_claimed_type(client, lists):
    uri = f"{URL}/{new_draft(client, lists)['id']}/attachments"
    for name, content, mime in [
        ("fake.png", b"this is not an image", "image/png"),
        ("fake.pdf", b"<html>not a pdf</html>", "application/pdf"),
        ("fake.jpg", PNG, "image/jpeg"),
        ("fake.webp", b"RIFF0000WAVE", "image/webp"),
        ("fake.txt", b"binary\x00data", "text/plain"),
    ]:
        response = client.post(uri, files={"file": (name, content, mime)})
        assert response.status_code == 415 and error_code(response) == "file_type_mismatch", name
    for name, content, mime in [
        ("ok.png", PNG, "image/png"),
        ("ok.jpg", b"\xff\xd8\xff\xe0data", "image/jpeg"),
        ("ok.webp", b"RIFF0000WEBPdata", "image/webp"),
        ("ok.pdf", b"%PDF-1.7 data", "application/pdf"),
        ("ok.txt", "plain text ස".encode(), "text/plain"),
        ("ok.eml", b"From: a@b.lk\r\nSubject: hi\r\n\r\nbody", "message/rfc822"),
    ]:
        assert client.post(uri, files={"file": (name, content, mime)}).status_code == 201, name


def test_a_complaint_holds_at_most_ten_files(client, lists):
    uri = f"{URL}/{new_draft(client, lists)['id']}/attachments"
    for _ in range(10):
        assert client.post(uri, files={"file": ("a.png", PNG, "image/png")}).status_code == 201
    eleventh = client.post(uri, files={"file": ("a.png", b"x", "image/png")})
    assert eleventh.status_code == 409 and error_code(eleventh) == "too_many_files"
