from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.enums import PersonType, RecommendationStatus
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import AuditLog, ComplaintMedium, Person, Recommendation
from tests.conftest import make_user, sign_in

URL = "/api/l1/recommendations"


class Lists:
    pass


@pytest.fixture
def lists(db, client) -> Lists:
    data = Lists()
    data.l1 = make_user(db, "office@sprpta.test", UserRole.L1)
    data.medium = ComplaintMedium(name="Letter")
    data.portal = ComplaintMedium(name="Portal", is_system=True)
    data.person = Person(full_name="Chaminda Rathnayake", person_type=PersonType.CONDUCTOR)
    db.add_all([data.medium, data.portal, data.person])
    db.commit()
    sign_in(client, "office@sprpta.test")
    return data


def commendation(lists: Lists, **changes) -> dict:
    body = {
        "recommendation_type": "commendation",
        "details": "A passenger thanked the conductor for helping a wheelchair user board.",
        "medium_id": lists.medium.id,
        "received_date": datetime.now(LOCAL).date().isoformat(),
        "subject_person_id": lists.person.id,
    }
    return {**body, **changes}


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def test_only_level_one_staff_may_log_a_recommendation(client, db, lists):
    client.post("/api/auth/logout")
    assert client.post(URL, json={}).status_code == 401
    make_user(db, "admin@sprpta.test", UserRole.ADMIN)
    sign_in(client, "admin@sprpta.test")
    assert client.post(URL, json={}).status_code == 403


def test_a_commendation_is_stored_as_new_with_the_person_and_its_audit_row(client, db, lists):
    response = client.post(URL, json=commendation(lists))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new" and body["recommendation_type"] == "commendation"
    assert body["title"] == "A passenger thanked the conductor for helping a wheelchair user board."

    row = db.get(Recommendation, body["id"])
    assert row.status == RecommendationStatus.NEW
    assert (row.subject_person_id, row.medium_id, row.entered_by_user_id) == (
        lists.person.id, lists.medium.id, lists.l1.id,
    )
    assert row.status_changed_by_user_id is None and row.verified_at is None
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "recommendation.create")).one()
    assert (audit.entity_id, audit.actor_role, audit.details) == (row.id, "l1", {"recommendation_type": "commendation"})


def test_an_improvement_suggestion_names_no_person_even_if_one_is_sent(client, db, lists):
    response = client.post(URL, json=commendation(lists, recommendation_type="improvement"))
    assert response.status_code == 201
    assert db.get(Recommendation, response.json()["id"]).subject_person_id is None


def test_medium_and_date_are_optional_and_a_long_first_line_becomes_a_short_title(client, db, lists):
    details = "Add a shelter at the Galle stand " + "so passengers stay dry " * 6 + "\nSecond line"
    response = client.post(URL, json={"recommendation_type": "improvement", "details": details})
    assert response.status_code == 201
    title = response.json()["title"]
    assert len(title) <= 80 and title.endswith("...") and "Second" not in title
    row = db.get(Recommendation, response.json()["id"])
    assert row.medium_id is None and row.received_date is None and row.details == details.strip()


def test_the_form_is_checked(client, lists):
    cases = {
        "person_required": commendation(lists, subject_person_id=None),
        "unknown_person": commendation(lists, subject_person_id=9999),
        "unknown_medium": commendation(lists, medium_id=9999),
        "future_date": commendation(lists, received_date=(datetime.now(LOCAL) + timedelta(days=2)).date().isoformat()),
    }
    for code, body in cases.items():
        response = client.post(URL, json=body)
        assert response.status_code == 422 and error_code(response) == code, code
    # Portal is the portal's own medium, not one L1 can choose.
    assert error_code(client.post(URL, json=commendation(lists, medium_id=lists.portal.id))) == "unknown_medium"
    assert client.post(URL, json=commendation(lists, details="   ")).status_code == 422
    assert client.post(URL, json=commendation(lists, recommendation_type="praise")).status_code == 422


def test_l1_cannot_read_a_recommendation_back(client, lists):
    created = client.post(URL, json=commendation(lists)).json()
    assert client.get(URL).status_code == 405
    assert client.get(f"{URL}/{created['id']}").status_code == 404
