from datetime import datetime, timedelta
from itertools import count

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import ComplaintStatus, PersonType, PlaceKind, RecommendationType, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import (
    Area,
    AuditLog,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintMedium,
    Person,
    Recommendation,
    RouteStand,
    Severity,
    SolutionDocument,
    Vehicle,
)
from app.services import l2_case_service
from tests.conftest import make_user, sign_in, target_id

URL = "/api/l2/cases"
NUMBERS = count(1)


class Setup:
    """Two areas, the Galle officer (signed in) and the lists a forwarded case needs."""


@pytest.fixture
def area(db, client, galle, tmp_path, monkeypatch) -> Setup:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    s = Setup()
    s.tmp = tmp_path
    s.galle = galle
    s.matara = Area(name="Matara")
    db.add(s.matara)
    db.flush()
    s.officer = make_user(db, "gihan@sprpta.test", UserRole.L2, area_id=galle.id, full_name="Gihan Samaraweera")
    s.l1 = make_user(db, "office@sprpta.test", UserRole.L1, full_name="Office Staff")
    s.medium = ComplaintMedium(name="WhatsApp")
    s.category = ComplaintCategory(name="Reckless driving")
    s.critical = Severity(name="Critical", rank=1, forward_days=0, decide_days=1, close_days=3, rating_weight=8)
    s.low = Severity(name="Low", rank=4, forward_days=3, decide_days=14, close_days=30, rating_weight=1)
    owner = Person(full_name="Nimal Perera", person_type=PersonType.OWNER)
    s.route = RouteStand(kind=PlaceKind.ROUTE, name="Galle - Matara", area_id=galle.id)
    db.add_all([s.medium, s.category, s.critical, s.low, owner, s.route])
    db.flush()
    s.bus = Vehicle(vehicle_number="SP NB-2345", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, owner_person_id=owner.id)
    s.other_bus = Vehicle(vehicle_number="SP NC-1111", vehicle_type=VehicleType.BUS, registered_area_id=s.matara.id)
    db.add_all([s.bus, s.other_bus])
    db.commit()
    sign_in(client, "gihan@sprpta.test")
    return s


def forwarded(db, s: Setup, *, severity=None, area=None, vehicle=None, age=timedelta(hours=1), **changes) -> Complaint:
    """A case as Level 1 leaves it: complete, with a reference number, forwarded to the area's officer."""
    registered = datetime.now(LOCAL) - age
    vehicle = vehicle or s.bus
    fields = dict(
        reference_number=f"SPRPTA-2026-{next(NUMBERS):06d}",
        status=ComplaintStatus.FORWARDED,
        entered_by_user_id=s.l1.id,
        medium_id=s.medium.id,
        complainant_name="Kamala Fernando",
        contact_phone="0771234567",
        complaint_date=registered.date(),
        target_type_id=target_id(db, "driver"),
        subject="Reckless overtaking",
        description="Overtook on a blind bend.",
        category_id=s.category.id,
        severity_id=(severity or s.low).id,
        vehicle_number_entered=vehicle.vehicle_number,
        vehicle_id=vehicle.id,
        route_stand_id=s.route.id,
        area_id=(area or s.galle).id,
        assigned_l2_user_id=s.officer.id,
        registered_at=registered,
        forwarded_at=registered,
    )
    c = Complaint(**{**fields, **changes})
    db.add(c)
    db.commit()
    return c


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def decide(client, case_id: int, **changes):
    body = {"action": "suspension", "outcome": "substantiated", "reasoning": "A safety risk to other road users."}
    return client.put(f"{URL}/{case_id}/decision", json={**body, **changes})


# ---------------------------------------------------------------- access


def test_only_area_officers_may_use_the_case_api(client, db, area):
    client.post("/api/auth/logout")
    assert client.get(URL).status_code == 401
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403
    assert client.get("/api/l2/dashboard").status_code == 403
    assert client.get("/api/l2/recommendations").status_code == 403


def test_an_officer_sees_only_routed_cases_of_their_own_area(client, db, area):
    mine = forwarded(db, area)
    other = forwarded(db, area, area=area.matara, vehicle=area.other_bus)
    draft = Complaint(status=ComplaintStatus.DRAFT, entered_by_user_id=area.l1.id, area_id=area.galle.id)
    db.add(draft)
    db.commit()

    page = client.get(URL).json()
    assert [row["id"] for row in page["items"]] == [mine.id]
    assert page["counts"]["forwarded"] == 1 and page["counts"]["all"] == 1
    assert client.get(f"{URL}/{other.id}").status_code == 404
    assert client.get(f"{URL}/{draft.id}").status_code == 404


# ---------------------------------------------------------------- the list


def test_a_case_past_its_decide_by_target_is_flagged_overdue(client, db, area):
    late = forwarded(db, area, severity=area.critical, age=timedelta(days=2))
    on_time = forwarded(db, area, severity=area.low, age=timedelta(days=2))

    page = client.get(URL).json()
    assert [row["id"] for row in page["items"]] == [late.id, on_time.id]  # overdue first
    assert page["items"][0]["overdue"] is True and page["items"][0]["due_kind"] == "decide"
    assert page["items"][1]["overdue"] is False
    assert page["counts"]["overdue"] == 1
    assert [row["id"] for row in client.get(URL, params={"status": "overdue"}).json()["items"]] == [late.id]


def test_the_list_filters_by_severity_and_searches_reference_subject_and_vehicle(client, db, area):
    critical = forwarded(db, area, severity=area.critical, subject="Assault at the stand")
    forwarded(db, area, subject="Dirty shelter")
    assert [r["id"] for r in client.get(URL, params={"severity": "critical"}).json()["items"]] == [critical.id]
    assert [r["id"] for r in client.get(URL, params={"search": "assault"}).json()["items"]] == [critical.id]
    assert client.get(URL, params={"search": critical.reference_number}).json()["total"] == 1
    assert client.get(URL, params={"search": "nb-2345"}).json()["total"] == 2


# ---------------------------------------------------------------- reviewing and deciding


def test_opening_a_forwarded_case_moves_it_to_under_review_once(client, db, area):
    case = forwarded(db, area)
    detail = client.get(f"{URL}/{case.id}").json()
    assert detail["status"] == "forwarded"  # reading alone changes nothing
    assert detail["has_contact"] is True and "contact_phone" not in detail

    assert client.post(f"{URL}/{case.id}/review").json()["status"] == "under_review"
    assert client.post(f"{URL}/{case.id}/review").json()["status"] == "under_review"
    moves = db.scalars(select(AuditLog).where(AuditLog.complaint_id == case.id, AuditLog.action == "complaint.review")).all()
    assert len(moves) == 1 and moves[0].to_status == ComplaintStatus.UNDER_REVIEW


def test_a_decision_can_be_changed_until_the_solution_document_is_made(client, db, area):
    case = forwarded(db, area)
    assert decide(client, case.id).status_code == 200
    changed = decide(client, case.id, action="warning", outcome="partly_substantiated").json()
    assert changed["status"] == "under_review"
    assert changed["decision"]["action"] == "warning" and changed["decision"]["decided_by"] == "Gihan Samaraweera"
    assert decide(client, case.id, reasoning="   ").status_code == 422


def test_the_solution_document_needs_a_decision_and_moves_the_case_on(client, db, area):
    case = forwarded(db, area)
    body = {"summary": "Reckless overtaking near Galle fort.", "solution_details": "Suspend the driver for 3 days."}
    assert error_code(client.post(f"{URL}/{case.id}/solution-document", json=body)) == "no_decision"

    decide(client, case.id)
    made = client.post(f"{URL}/{case.id}/solution-document", json=body)
    assert made.status_code == 201, made.text
    detail = made.json()
    assert detail["status"] == "awaiting_implementation" and detail["due_kind"] == "close"
    assert detail["solution_document"]["verdict_text"] == "Suspension. The complaint is substantiated."

    stored = db.scalar(select(SolutionDocument).where(SolutionDocument.complaint_id == case.id))
    assert (area.tmp / stored.pdf_path).read_bytes().startswith(b"%PDF-")
    pdf = client.get(f"{URL}/{case.id}/solution-document")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "solution_document.view")) is not None

    assert error_code(decide(client, case.id)) == "not_deciding"
    assert error_code(client.post(f"{URL}/{case.id}/solution-document", json=body)) == "not_deciding"


# ---------------------------------------------------------------- escalating


def test_escalating_needs_a_reason_and_ends_the_officers_part(client, db, area):
    case = forwarded(db, area)
    assert client.post(f"{URL}/{case.id}/escalate", json={"reason": " "}).status_code == 422
    escalated = client.post(f"{URL}/{case.id}/escalate", json={"reason": "Legal action is beyond my powers."}).json()
    assert escalated["status"] == "escalated"
    assert escalated["escalation"]["reason"] == "Legal action is beyond my powers."
    assert escalated["due_kind"] is None and escalated["overdue"] is False
    assert error_code(decide(client, case.id)) == "not_deciding"


def test_escalating_withdraws_a_draft_decision_and_keeps_it_in_the_audit_trail(client, db, area):
    case = forwarded(db, area)
    decide(client, case.id, reasoning="First thought.")
    escalated = client.post(f"{URL}/{case.id}/escalate", json={"reason": "Beyond my powers."}).json()
    assert escalated["status"] == "escalated" and escalated["decision"] is None
    row = db.scalar(select(AuditLog).where(AuditLog.complaint_id == case.id, AuditLog.action == "complaint.escalate"))
    assert row.from_status == ComplaintStatus.UNDER_REVIEW
    assert row.details["withdrawn_decision"]["reasoning"] == "First thought."


def test_a_case_level_three_decided_carries_no_target_for_level_two(client, db, area):
    case = forwarded(db, area, severity=area.critical, age=timedelta(days=5))
    client.post(f"{URL}/{case.id}/escalate", json={"reason": "Beyond my powers."})
    db.refresh(case)
    case.status = ComplaintStatus.AWAITING_IMPLEMENTATION  # as Level 3 leaves it after its own decision
    db.commit()
    detail = client.get(f"{URL}/{case.id}").json()
    assert detail["due_kind"] is None and detail["overdue"] is False
    assert detail["escalation"] is not None


def test_escalating_an_unopened_case_passes_through_under_review(client, db, area):
    case = forwarded(db, area)
    client.post(f"{URL}/{case.id}/escalate", json={"reason": "Beyond my powers."})
    moves = db.scalars(
        select(AuditLog.to_status).where(AuditLog.complaint_id == case.id).order_by(AuditLog.id)
    ).all()
    assert moves == [ComplaintStatus.UNDER_REVIEW, ComplaintStatus.ESCALATED]


# ---------------------------------------------------------------- dashboard and recommendations


def test_the_dashboard_counts_the_area_and_points_at_the_most_urgent_case(client, db, area):
    late = forwarded(db, area, severity=area.critical, age=timedelta(days=2))
    forwarded(db, area)
    forwarded(db, area, area=area.matara, vehicle=area.other_bus)

    board = client.get("/api/l2/dashboard").json()
    assert board["counts"]["forwarded"] == 2 and board["counts"]["overdue"] == 1
    assert board["urgent"] == 1 and board["next_case_id"] == late.id
    assert [row["id"] for row in board["overdue"]] == [late.id]
    assert [t["severity"] for t in board["targets"]] == ["critical", "low"]


def test_recommendations_are_read_only_and_filterable(client, db, area):
    db.add_all(
        [
            Recommendation(recommendation_type=RecommendationType.IMPROVEMENT, title="Shaded benches", details="At the stand.", entered_by_user_id=area.l1.id),
            Recommendation(recommendation_type=RecommendationType.COMMENDATION, title="Helpful conductor", details="Helped a wheelchair user.", entered_by_user_id=area.l1.id),
        ]
    )
    db.commit()
    page = client.get("/api/l2/recommendations", params={"type": "commendation"}).json()
    assert [r["title"] for r in page["items"]] == ["Helpful conductor"] and page["counts"]["new"] == 1
    detail = client.get(f"/api/l2/recommendations/{page['items'][0]['id']}").json()
    assert detail["entered_by"] == "Office Staff" and detail["details"] == "Helped a wheelchair user."
    assert client.put(f"/api/l2/recommendations/{detail['id']}", json={"status": "acknowledged"}).status_code == 405


def test_recommendations_can_be_found_by_the_commended_person(client, db, area):
    person = Person(full_name="Sunil Jayasena", person_type=PersonType.CONDUCTOR)
    db.add(person)
    db.flush()
    db.add(
        Recommendation(
            recommendation_type=RecommendationType.COMMENDATION, title="Very kind", details="Helped an old man.",
            subject_person_id=person.id, entered_by_user_id=area.l1.id,
        )
    )
    db.commit()
    page = client.get("/api/l2/recommendations", params={"search": "jayasena"}).json()
    assert [r["title"] for r in page["items"]] == ["Very kind"]


def test_the_dashboard_shows_the_areas_categories_and_outcomes(client, db, area):
    decided = forwarded(db, area)
    forwarded(db, area)
    forwarded(db, area, area=area.matara, vehicle=area.other_bus)
    decide(client, decided.id, outcome="partly_substantiated")
    client.post(f"{URL}/{decided.id}/solution-document", json={"summary": "s", "solution_details": "d"})

    stats = client.get("/api/l2/dashboard").json()["statistics"]
    assert stats["cases"] == 2
    assert stats["categories"] == [{"name": "Reckless driving", "count": 2}]
    assert stats["outcomes"] == {"partly_substantiated": 1}


# ---------------------------------------------------------------- access and isolation


@pytest.mark.parametrize("role", [UserRole.L1, UserRole.L3, UserRole.ADMIN, UserRole.IMPLEMENTING_STAFF])
def test_no_other_role_can_reach_any_level_two_route(client, db, area, role):
    case = forwarded(db, area)
    client.post("/api/auth/logout")
    make_user(db, f"{role.value}@sprpta.test", role)
    sign_in(client, f"{role.value}@sprpta.test")
    calls = [
        ("get", URL), ("get", f"{URL}/{case.id}"), ("post", f"{URL}/{case.id}/review"),
        ("put", f"{URL}/{case.id}/decision"), ("post", f"{URL}/{case.id}/solution-document"),
        ("get", f"{URL}/{case.id}/solution-document"), ("post", f"{URL}/{case.id}/escalate"),
        ("get", f"{URL}/{case.id}/attachments/1"), ("get", "/api/l2/dashboard"),
        ("get", "/api/l2/recommendations"), ("get", "/api/l2/recommendations/1"),
    ]
    for method, url in calls:
        body = {"json": {}} if method in ("post", "put") else {}
        assert getattr(client, method)(url, **body).status_code == 403, (method, url)


def test_another_areas_officer_cannot_reach_or_change_a_case(client, db, area):
    case = forwarded(db, area)
    (area.tmp / "x.pdf").write_bytes(b"%PDF-1")
    attachment = ComplaintAttachment(
        complaint_id=case.id, file_name="x.pdf", storage_path="x.pdf", mime_type="application/pdf", size_bytes=6,
        uploaded_by_user_id=area.l1.id,
    )
    db.add(attachment)
    db.commit()
    client.post("/api/auth/logout")
    make_user(db, "shamila@sprpta.test", UserRole.L2, area_id=area.matara.id)
    sign_in(client, "shamila@sprpta.test")

    doc = {"summary": "s", "solution_details": "d"}
    attempts = [
        ("get", f"{URL}/{case.id}", {}),
        ("post", f"{URL}/{case.id}/review", {}),
        ("put", f"{URL}/{case.id}/decision", {"json": {"action": "fine", "outcome": "substantiated", "reasoning": "x"}}),
        ("post", f"{URL}/{case.id}/solution-document", {"json": doc}),
        ("get", f"{URL}/{case.id}/solution-document", {}),
        ("post", f"{URL}/{case.id}/escalate", {"json": {"reason": "x"}}),
        ("get", f"{URL}/{case.id}/attachments/{attachment.id}", {}),
    ]
    for method, url, kwargs in attempts:
        assert getattr(client, method)(url, **kwargs).status_code == 404, (method, url)
    db.refresh(case)
    assert case.status == ComplaintStatus.FORWARDED
    assert client.get(URL).json()["total"] == 0


# ---------------------------------------------------------------- overdue, decided cases and severities


def test_decide_by_ends_with_the_solution_document_not_the_draft_decision(client, db, area):
    case = forwarded(db, area, severity=area.critical, age=timedelta(days=2))  # past decide-by (1 day), inside close-by (3)
    decide(client, case.id)
    detail = client.get(f"{URL}/{case.id}").json()
    assert detail["overdue"] is True and detail["due_kind"] == "decide"  # a draft decision does not stop the clock

    client.post(f"{URL}/{case.id}/solution-document", json={"summary": "s", "solution_details": "d"})
    detail = client.get(f"{URL}/{case.id}").json()
    assert detail["overdue"] is False and detail["due_kind"] == "close"
    board = client.get("/api/l2/dashboard").json()
    assert board["urgent"] == 0 and board["next_case_id"] is None and board["overdue"] == []
    assert board["decided_today"] == 1 and board["average_decide_days"] == 2.0
    assert client.get(URL, params={"status": "overdue"}).json()["total"] == 0


def test_changing_a_decision_does_not_count_as_deciding_another_case(client, db, area):
    case = forwarded(db, area)
    decide(client, case.id)
    decide(client, case.id, action="warning")
    db.refresh(case)
    assert case.decided_at is None
    assert client.get("/api/l2/dashboard").json()["decided_today"] == 0


def test_severity_comes_from_the_rank_so_a_renamed_severity_still_works(client, db, area):
    area.critical.name = "Very urgent"
    db.commit()
    case = forwarded(db, area, severity=area.critical)
    assert client.get(f"{URL}/{case.id}").json()["severity"] == "critical"
    assert [r["id"] for r in client.get(URL, params={"severity": "critical"}).json()["items"]] == [case.id]
    assert client.get("/api/l2/dashboard").json()["targets"][0]["severity"] == "critical"


# ---------------------------------------------------------------- what the case shows


def test_earlier_cases_include_other_areas_as_summaries(client, db, area):
    person = Person(full_name="Kasun", person_type=PersonType.DRIVER)
    db.add(person)
    db.flush()
    old = timedelta(days=30)
    routed = forwarded(db, area, subject_person_id=person.id, age=old)
    elsewhere = forwarded(db, area, area=area.matara, vehicle=area.other_bus, subject_person_id=person.id, age=old)
    rejected = forwarded(
        db, area, status=ComplaintStatus.REJECTED, rejection_type="invalid", rejection_reason="spam", age=old
    )
    incomplete = forwarded(db, area, status=ComplaintStatus.INCOMPLETE, age=old)
    current = forwarded(db, area, subject_person_id=person.id)

    earlier = client.get(f"{URL}/{current.id}").json()["earlier"]
    assert {e["id"]: (e["own_area"], e["area"]) for e in earlier} == {
        routed.id: (True, "Galle"),
        elsewhere.id: (False, "Matara"),
    }
    shown = {e["reference_number"] for e in earlier}
    assert not shown & {rejected.reference_number, incomplete.reference_number}
    assert client.get(f"{URL}/{elsewhere.id}").status_code == 404  # listed, but still not open to this officer


def test_the_case_shows_the_level_one_details_level_two_needs(client, db, area):
    case = forwarded(
        db, area, complainant_type="passenger", incident_time=datetime.now(LOCAL).time().replace(microsecond=0),
        bus_verification="verified",
    )
    detail = client.get(f"{URL}/{case.id}").json()
    assert detail["complainant_type"] == "passenger" and detail["bus_verification"] == "verified"
    assert detail["incident_time"] is not None
    assert detail["driver_on_duty"] is None  # no trip was selected


def test_changing_a_decision_keeps_the_previous_values_in_the_audit_trail(client, db, area):
    case = forwarded(db, area)
    decide(client, case.id, reasoning="First thought.")
    decide(client, case.id, action="warning", reasoning="Second thought.")
    rows = db.scalars(
        select(AuditLog).where(AuditLog.complaint_id == case.id, AuditLog.action.like("decision.%")).order_by(AuditLog.id)
    ).all()
    assert [r.action for r in rows] == ["decision.create", "decision.update"]
    assert rows[0].details["previous"] is None
    assert rows[1].details["previous"] == {"action": "suspension", "outcome": "substantiated", "reasoning": "First thought."}
    assert rows[1].details["new"]["action"] == "warning" and rows[1].details["new"]["reasoning"] == "Second thought."


# ---------------------------------------------------------------- files


def test_attachments_open_only_for_their_own_case_and_are_never_sniffed(client, db, area):
    case, other = forwarded(db, area), forwarded(db, area)
    (area.tmp / "a.pdf").write_bytes(b"%PDF-1.4 hi")

    def attachment(**changes) -> ComplaintAttachment:
        return ComplaintAttachment(
            complaint_id=case.id, file_name="a.pdf", storage_path="a.pdf", mime_type="application/pdf", size_bytes=11,
            uploaded_by_user_id=area.l1.id, **changes,
        )

    shown, removed, lost = attachment(), attachment(removed_at=datetime.now(LOCAL)), attachment()
    lost.storage_path = "gone.pdf"
    db.add_all([shown, removed, lost])
    db.commit()

    opened = client.get(f"{URL}/{case.id}/attachments/{shown.id}")
    assert opened.status_code == 200 and opened.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"{URL}/{case.id}/attachments/{removed.id}").status_code == 404
    assert client.get(f"{URL}/{other.id}/attachments/{shown.id}").status_code == 404
    assert error_code(client.get(f"{URL}/{case.id}/attachments/{lost.id}")) == "file_missing"
    detail = client.get(f"{URL}/{case.id}").json()
    assert [a["id"] for a in detail["attachments"]] == [shown.id, lost.id]

    views = db.scalars(select(AuditLog).where(AuditLog.action == "attachment.view")).all()
    assert [(v.entity_id, v.actor_user_id) for v in views] == [(shown.id, area.officer.id)]  # a missing file is not a view
    assert all(h["action"] != "attachment.view" for h in detail["history"])


def test_the_solution_document_handles_sinhala_tamil_emoji_and_long_text(client, db, area):
    texts = [
        {"summary": "බස් රථය අනතුරුදායකව ඉස්සර කළේය. பேருந்து வேகமாக சென்றது. 🚌", "solution_details": "සිංහල தமிழ் 🙂"},
        {"summary": "a" * 2000, "solution_details": "b" * 5000},
        {"summary": "word " * 390, "solution_details": ("line\n" * 900)[:5000]},
    ]
    for doc in texts:
        case = forwarded(db, area)
        decide(client, case.id)
        assert client.post(f"{URL}/{case.id}/solution-document", json=doc).status_code == 201
        assert client.get(f"{URL}/{case.id}/solution-document").content.startswith(b"%PDF-")


def test_a_failed_save_leaves_no_pdf_and_no_status_change(client, db, area, monkeypatch):
    case = forwarded(db, area)
    decide(client, case.id)

    def fail(*args, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(l2_case_service, "_move", fail)
    with pytest.raises(RuntimeError):
        client.post(f"{URL}/{case.id}/solution-document", json={"summary": "s", "solution_details": "d"})
    assert not list(area.tmp.glob("solution-documents/**/*.pdf"))
    db.expire_all()
    assert db.get(Complaint, case.id).status == ComplaintStatus.UNDER_REVIEW
    assert db.scalar(select(SolutionDocument.id).where(SolutionDocument.complaint_id == case.id)) is None
