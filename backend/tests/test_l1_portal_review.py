"""Level 1 checks a portal complaint with the same form as any other complaint, then forwards, rejects or keeps it."""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL
from app.models import AuditLog, Complaint
from tests.conftest import make_complainant
from tests.test_l1_complaints import URL, error_code, form, lists  # noqa: F401  (lists is a fixture)


@pytest.fixture
def sent(db, lists) -> Complaint:
    """A complaint the public sent through the portal: no severity, no reference, the bus not looked up yet."""
    account = make_complainant(db, "client@sprpta.test", phone="+94712345678")
    complaint = Complaint(
        status=ComplaintStatus.SUBMITTED,
        submitted_via_portal=True,
        complainant_account_id=account.id,
        medium_id=lists.portal.id,
        complainant_name="Saman Kumara",
        contact_phone="+94712345678",
        contact_email="client@sprpta.test",
        complaint_date=datetime.now(LOCAL).date(),
        target_type_id=lists.driver_target,
        category_id=lists.category.id,
        subject="Driver was rude",
        description="He shouted at the passengers.",
        area_id=lists.area.id,
        route_stand_id=lists.route.id,
        vehicle_number_entered="SP NB-2345",
    )
    db.add(complaint)
    db.commit()
    return complaint


def check(lists, **changes) -> dict:
    """What Level 1 sends after checking it: the complainant's own words, plus the severity."""
    return form(lists, subject="Driver was rude", description="He shouted at the passengers.", **changes)


def test_it_opens_in_the_form_and_can_be_changed(client, lists, sent):
    opened = client.get(f"{URL}/{sent.id}").json()
    assert opened["status"] == "submitted" and opened["via_portal"] is True
    assert opened["severity_id"] is None and opened["area_name"] == "Galle"

    listed = client.get(URL, params={"status": "submitted", "scope": "all"}).json()["items"]
    assert [row["editable"] for row in listed] == [True]

    saved = client.put(f"{URL}/{sent.id}", json=check(lists)).json()
    assert saved["status"] == "submitted" and saved["severity_id"] == lists.severity.id
    assert saved["vehicle"]["vehicle_number"] == "SP NB-2345"


def test_the_portal_medium_and_the_account_contact_are_kept(client, db, lists, sent):
    client.put(f"{URL}/{sent.id}", json=check(lists, complainant_name="Someone else", mobile="0779999999"))
    db.refresh(sent)
    assert sent.medium_id == lists.portal.id
    assert sent.complainant_name == "Saman Kumara" and sent.contact_phone == "+94712345678"
    assert sent.contact_email == "client@sprpta.test" and not sent.is_anonymous


def test_forwarding_sends_it_to_the_area_officer_like_any_complaint(client, db, lists, sent):
    client.put(f"{URL}/{sent.id}", json=check(lists))
    forwarded = client.post(f"{URL}/{sent.id}/forward")
    assert forwarded.status_code == 200, forwarded.text
    body = forwarded.json()
    assert body["status"] == "forwarded" and body["assigned_l2_name"] == "Ruwan Silva"
    assert body["reference_number"].endswith(f"{sent.id:06d}")

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "complaint.forward"))
    assert audit.from_status == ComplaintStatus.SUBMITTED and audit.to_status == ComplaintStatus.FORWARDED


def test_it_cannot_be_forwarded_without_a_severity(client, lists, sent):
    client.put(f"{URL}/{sent.id}", json=check(lists, severity_id=None))
    refused = client.post(f"{URL}/{sent.id}/forward")
    assert refused.status_code == 422 and "severity" in refused.json()["detail"]["message"]


def test_it_can_wait_as_incomplete_and_be_forwarded_later(client, lists, sent):
    kept = client.post(f"{URL}/{sent.id}/incomplete").json()
    assert kept["status"] == "incomplete" and kept["reference_number"]
    client.put(f"{URL}/{sent.id}", json=check(lists))
    assert client.post(f"{URL}/{sent.id}/forward").json()["status"] == "forwarded"


def test_it_can_be_rejected(client, lists, sent):
    rejected = client.post(f"{URL}/{sent.id}/reject", json={"rejection_type": "spam", "reason": "Advertising, not a complaint."})
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"


def test_an_unknown_bus_keeps_the_area_the_complainant_chose(client, db, lists, sent):
    client.put(f"{URL}/{sent.id}", json=check(lists, vehicle_number="XX-0000"))
    db.refresh(sent)
    assert sent.vehicle_id is None and sent.area_id == lists.area.id
    assert client.post(f"{URL}/{sent.id}/forward").status_code == 422  # a vehicle on record is still needed


def test_one_the_complainant_deleted_cannot_be_checked(client, db, lists, sent):
    sent.withdrawn_at = datetime.now(LOCAL)
    db.commit()
    refused = client.post(f"{URL}/{sent.id}/forward")
    assert refused.status_code == 409 and error_code(refused) == "withdrawn"
