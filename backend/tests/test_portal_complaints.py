"""The complainant's own complaints (UC-CP-03, UC-CP-04)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.enums import ComplaintStatus, PlaceKind
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import Area, AuditLog, Complaint, ComplaintCategory, ComplaintMedium, RouteStand
from app.services.portal_complaint_service import step_of
from tests.conftest import make_complainant, make_user, sign_in, target_id

URL = "/api/cp/complaints"
TODAY = datetime.now(LOCAL).date()


class World:
    pass


@pytest.fixture
def world(db, client, galle) -> World:
    w = World()
    w.area = galle
    w.matara = Area(name="Matara")
    w.portal = ComplaintMedium(name="Portal", is_system=True)
    w.category = ComplaintCategory(name="Overcharging")
    w.route = RouteStand(kind=PlaceKind.ROUTE, name="Galle - Matara", area_id=galle.id)
    db.add_all([w.matara, w.portal, w.category, w.route])
    db.commit()
    w.target = target_id(db, "conductor")
    w.account = make_complainant(db, "client@sprpta.test", phone="+94712345678")
    assert sign_in(client, "client@sprpta.test").status_code == 200
    return w


def form(w: World, **changes) -> dict:
    body = {
        "complaint_date": TODAY.isoformat(),
        "target_type_id": w.target,
        "subject": "Conductor charged too much",
        "vehicle_number": " sp nb-2345 ",
        "area_id": w.area.id,
        "route_stand_id": w.route.id,
        "category_id": w.category.id,
        "description": "I was charged twice the usual fare.",
    }
    body.update(changes)
    return body


def test_a_portal_complaint_is_saved_as_submitted_without_a_reference(client, db, world):
    r = client.post(URL, json=form(world))
    assert r.status_code == 201
    out = r.json()
    assert out["step"] == 1 and out["status_label"] == "Submitted (awaiting Level 1 check)"
    assert out["reference_number"] is None and out["outcome"] == "open"
    assert out["vehicle_number"] == "SP NB-2345" and out["area_name"] == "Galle"

    saved = db.scalar(select(Complaint))
    assert saved.status == ComplaintStatus.SUBMITTED and saved.submitted_via_portal
    assert saved.complainant_account_id == world.account.id
    assert saved.medium_id == world.portal.id
    assert saved.contact_email == "client@sprpta.test" and saved.contact_phone == "+94712345678"
    assert saved.severity_id is None and saved.entered_by_user_id is None

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "complaint.submit_portal"))
    assert audit.actor_account_id == world.account.id and audit.actor_user_id is None


def test_level_1_sees_it_in_the_portal_queue(client, db, world):
    client.post(URL, json=form(world))
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get("/api/l1/dashboard").json()["queues"]["portal"] == 1


def test_the_form_lists_what_the_complainant_may_choose(client, world):
    r = client.get(f"{URL}/options")
    assert r.status_code == 200
    body = r.json()
    assert {a["name"] for a in body["areas"]} == {"Galle", "Matara"}
    assert "conductor" in {t["code"] for t in body["targets"]}
    assert [c["name"] for c in body["categories"]] == ["Overcharging"]
    assert body["routes_stands"][0]["name"] == "Galle - Matara"
    assert "severities" not in body and "mediums" not in body


def test_only_my_own_complaints_are_listed_and_opened(client, db, world):
    mine = client.post(URL, json=form(world)).json()["id"]
    other = make_complainant(db, "other@sprpta.test")
    db.add(Complaint(status=ComplaintStatus.SUBMITTED, complainant_account_id=other.id, subject="Not mine"))
    db.commit()

    assert [c["id"] for c in client.get(URL).json()] == [mine]
    assert client.get(f"{URL}/{mine}").status_code == 200
    theirs = db.scalar(select(Complaint.id).where(Complaint.subject == "Not mine"))
    assert client.get(f"{URL}/{theirs}").status_code == 404


def test_the_newest_complaint_comes_first(client, world):
    first = client.post(URL, json=form(world, subject="First")).json()["id"]
    second = client.post(URL, json=form(world, subject="Second")).json()["id"]
    assert [c["id"] for c in client.get(URL).json()] == [second, first]


def test_every_internal_status_maps_to_one_of_four_steps():
    steps = {s: step_of(s) for s in ComplaintStatus if s != ComplaintStatus.DRAFT}
    assert set(steps.values()) == {1, 2, 3, 4}
    assert steps[ComplaintStatus.SUBMITTED] == 1
    assert steps[ComplaintStatus.FORWARDED] == 2
    assert steps[ComplaintStatus.ESCALATED] == 3
    assert steps[ComplaintStatus.CLOSED] == steps[ComplaintStatus.REJECTED] == 4


def test_a_rejected_complaint_reads_as_not_accepted(client, db, world):
    cid = client.post(URL, json=form(world)).json()["id"]
    c = db.get(Complaint, cid)
    c.status = ComplaintStatus.REJECTED
    c.rejection_type = "spam"
    c.rejection_reason = "Internal note that must not be shown"
    db.commit()
    out = client.get(f"{URL}/{cid}").json()
    assert out["step"] == 4 and out["outcome"] == "not_accepted"
    assert "Internal note" not in str(out)


def test_drafts_are_never_shown_to_the_complainant(client, db, world):
    db.add(Complaint(status=ComplaintStatus.DRAFT, complainant_account_id=world.account.id, subject="Hidden"))
    db.commit()
    assert client.get(URL).json() == []


@pytest.mark.parametrize(
    "changes, code",
    [
        ({"complaint_date": (TODAY + timedelta(days=1)).isoformat()}, "future_date"),
        ({"target_type_id": 999999}, "unknown_target"),
        ({"category_id": 999999}, "unknown_category"),
        ({"area_id": 999999}, "unknown_area"),
        ({"route_stand_id": 999999}, "unknown_route_stand"),
    ],
)
def test_a_complaint_must_point_at_real_choices(client, world, changes, code):
    r = client.post(URL, json=form(world, **changes))
    assert r.status_code == 422 and r.json()["detail"]["code"] == code


def test_the_route_must_belong_to_the_chosen_area(client, world):
    r = client.post(URL, json=form(world, area_id=world.matara.id))
    assert r.status_code == 422 and r.json()["detail"]["code"] == "route_not_in_area"


@pytest.mark.parametrize("changes", [{"subject": "  "}, {"description": ""}, {"vehicle_number": "x" * 21}])
def test_blank_or_oversized_text_is_refused(client, world, changes):
    assert client.post(URL, json=form(world, **changes)).status_code == 422


def test_the_vehicle_number_and_route_are_optional(client, world):
    r = client.post(URL, json=form(world, vehicle_number=None, route_stand_id=None))
    assert r.status_code == 201 and r.json()["vehicle_number"] is None


def test_only_portal_users_may_use_it(client, db, world):
    client.post("/api/auth/logout")
    assert client.get(URL).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403
    assert client.post(URL, json=form(world)).status_code == 403
