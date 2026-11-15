"""Complaint classification: who the complaint is against, kept apart from the issue category and the area."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import PersonType
from app.core.roles import UserRole
from app.main import app
from app.models import Complaint, ComplaintCategory, ComplaintCategoryTarget, ComplaintTargetType, Person
from tests.conftest import make_user, sign_in, target_id
from tests.test_bus_lookup import (  # noqa: F401  (the fixtures and helpers of the lookup tests)
    COMPLAINTS,
    complaint_lists,
    error_code,
    publish_trip,
    world,
)

CODES = ("driver", "conductor", "owner", "bus_service", "other")


def body(db, code: str | None, **changes) -> dict:
    base = {"subject": "Charged more than the fare", "vehicle_number": "ND-7782"}
    if code:
        base["target_type_id"] = target_id(db, code)
    return {**base, **changes}


def make(client, db, code, **changes) -> dict:
    created = client.post(COMPLAINTS, json=body(db, code, **changes))
    assert created.status_code == 201, created.text
    return created.json()


# ---------------------------------------------------------------- the lists


def test_the_target_types_are_the_five_approved_kinds(client, db, world):
    targets = client.get(f"{COMPLAINTS}/targets").json()
    assert [t["code"] for t in targets] == list(CODES)
    assert [t["name"] for t in targets] == ["Driver", "Conductor", "Bus owner", "Bus / Transport service", "Other"]
    assert [t["name"] for t in client.get(f"{COMPLAINTS}/options").json()["targets"]] == [t["name"] for t in targets]


def test_every_category_is_open_to_a_target_until_mappings_are_approved(client, db, world):
    db.add_all([ComplaintCategory(name="Reckless driving"), ComplaintCategory(name="Ticket not issued")])
    db.commit()
    everything = client.get(f"{COMPLAINTS}/categories").json()
    assert {c["name"] for c in everything} == {"Reckless driving", "Ticket not issued"}
    for code in CODES:
        shown = client.get(f"{COMPLAINTS}/categories", params={"target_id": target_id(db, code)}).json()
        assert {c["name"] for c in shown} == {"Reckless driving", "Ticket not issued"}, code  # no mapping: no filtering


def test_an_approved_mapping_limits_the_categories_of_that_target_only(client, db, world):
    reckless = ComplaintCategory(name="Reckless driving")
    ticket = ComplaintCategory(name="Ticket not issued")
    db.add_all([reckless, ticket])
    db.flush()
    db.add(ComplaintCategoryTarget(category_id=reckless.id, target_type_id=target_id(db, "driver")))
    db.commit()

    driver = client.get(f"{COMPLAINTS}/categories", params={"target_id": target_id(db, "driver")}).json()
    assert [c["name"] for c in driver] == ["Reckless driving"]
    conductor = client.get(f"{COMPLAINTS}/categories", params={"target_id": target_id(db, "conductor")}).json()
    assert {c["name"] for c in conductor} == {"Reckless driving", "Ticket not issued"}  # still open: no rows for it
    options = {c["name"]: c["target_ids"] for c in client.get(f"{COMPLAINTS}/options").json()["categories"]}
    assert options == {"Reckless driving": [target_id(db, "driver")], "Ticket not issued": []}

    refused = client.post(COMPLAINTS, json=body(db, "driver", category_id=ticket.id))
    assert refused.status_code == 422 and error_code(refused) == "invalid_category"
    assert client.post(COMPLAINTS, json=body(db, "driver", category_id=reckless.id)).status_code == 201
    assert client.post(COMPLAINTS, json=body(db, "conductor", category_id=ticket.id)).status_code == 201


# ---------------------------------------------------------------- a complaint against each kind of target


def test_a_complaint_against_a_driver_stores_the_target_and_the_accused(client, db, world, complaint_lists):
    category = db.scalar(select(ComplaintCategory))
    saved = make(client, db, "driver", subject_person_id=world.driver.id, category_id=category.id)
    assert (saved["target_code"], saved["target_name"]) == ("driver", "Driver")
    assert (saved["subject_person_id"], saved["subject_person_name"]) == (world.driver.id, "Saman Kumara")
    assert saved["category_id"] == category.id and saved["category_name"] == "Overcharging"  # the issue stays separate
    row = db.get(Complaint, saved["id"])
    assert row.target_type_id == target_id(db, "driver") and row.subject_person_id == world.driver.id
    assert row.entered_by_user_id is not None
    assert client.get(f"{COMPLAINTS}/{saved['id']}").json()["target_code"] == "driver"


def test_a_complaint_against_a_conductor_an_owner_or_other(client, db, world, complaint_lists):
    conductor = make(client, db, "conductor", subject_person_id=world.conductor.id)
    owner = make(client, db, "owner", subject_person_id=world.owner.id)
    other = make(client, db, "other", subject_person_text="A passenger on the bus")
    assert (conductor["target_code"], conductor["subject_person_name"]) == ("conductor", "Chaminda Rathnayake")
    assert (owner["target_code"], owner["subject_person_name"]) == ("owner", "Nimal Perera")
    assert (other["target_code"], other["subject_person_name"]) == ("other", "A passenger on the bus")
    staff = Person(full_name="Dilani Staff", person_type=PersonType.SPRPTA_STAFF)
    db.add(staff)
    db.commit()
    assert make(client, db, "other", subject_person_id=staff.id)["subject_person_name"] == "Dilani Staff"  # any person


def test_a_complaint_against_the_bus_or_service_names_nobody(client, db, world):
    saved = make(client, db, "bus_service")
    assert saved["target_code"] == "bus_service" and saved["subject_person_id"] is None
    assert saved["accused_status"] == "none"
    for extra in ({"subject_person_id": world.driver.id}, {"subject_person_text": "The driver"}):
        refused = client.post(COMPLAINTS, json=body(db, "bus_service", **extra))
        assert refused.status_code == 422 and error_code(refused) == "accused_not_allowed"


def test_the_person_must_be_of_the_right_type_for_the_target(client, db, world):
    wrong = {
        "driver": world.conductor.id,
        "conductor": world.driver.id,
        "owner": world.driver.id,
    }
    for code, person in wrong.items():
        refused = client.post(COMPLAINTS, json=body(db, code, subject_person_id=person))
        assert refused.status_code == 422 and error_code(refused) == "wrong_person_type", code
    assert client.post(COMPLAINTS, json=body(db, "driver", subject_person_id=9999)).status_code == 422


def test_the_target_is_checked(client, db, world):
    unknown = client.post(COMPLAINTS, json={"target_type_id": 9999})
    assert unknown.status_code == 422 and error_code(unknown) == "unknown_target"
    db.get(ComplaintTargetType, target_id(db, "other")).is_active = False
    db.commit()
    off = client.post(COMPLAINTS, json=body(db, None, target_type_id=target_id(db, "other")))
    off_code = error_code(off)
    assert off.status_code == 422 and off_code == "unknown_target"  # a switched-off target cannot be used
    try:
        assert "other" not in [t["code"] for t in client.get(f"{COMPLAINTS}/targets").json()]
    finally:  # reference rows survive between tests, so switch it back on
        db.get(ComplaintTargetType, target_id(db, "other")).is_active = True
        db.commit()


def test_a_draft_may_leave_the_target_open_but_forwarding_needs_it(client, db, world, complaint_lists):
    category = db.scalar(select(ComplaintCategory))
    draft = make(client, db, None, medium_id=1, complaint_date=None)
    assert draft["target_code"] is None and draft["accused_status"] == "none"
    from app.models import ComplaintMedium, RouteStand, Severity

    ready = {
        "medium_id": db.scalar(select(ComplaintMedium.id)),
        "complaint_date": "2026-01-02",
        "vehicle_number": "ND-7782",
        "route_stand_id": db.scalar(select(RouteStand.id)),
        "category_id": category.id,
        "severity_id": db.scalar(select(Severity.id)),
        "complainant_name": "Kamala",
        "subject": "Fare",
        "description": "Asked for double",
    }
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    saved = client.put(f"{COMPLAINTS}/{draft['id']}", json=ready).json()
    blocked = client.post(f"{COMPLAINTS}/{saved['id']}/forward")
    assert blocked.status_code == 422 and error_code(blocked) == "missing_details"
    assert "who the complaint is against" in blocked.json()["detail"]["message"]

    client.put(f"{COMPLAINTS}/{saved['id']}", json={**ready, "target_type_id": target_id(db, "bus_service")})
    assert client.post(f"{COMPLAINTS}/{saved['id']}/forward").status_code == 200


# ---------------------------------------------------------------- the accused person is never assumed


def test_a_bus_with_a_verified_driver_does_not_accuse_anyone_by_itself(client, db, world, complaint_lists):
    trip = publish_trip(world)
    saved = make(client, db, "driver", trip_id=trip["id"])
    assert saved["duty"]["driver_person_id"] == world.driver.id  # the verified driver is offered
    assert saved["subject_person_id"] is None and saved["accused_status"] == "none"  # but nobody is accused


def test_the_status_of_the_accused_is_worked_out_by_the_server(client, db, world, complaint_lists):
    trip = publish_trip(world)
    other_driver = Person(full_name="Somebody Else", person_type=PersonType.DRIVER)
    db.add(other_driver)
    db.commit()

    verified = make(client, db, "driver", trip_id=trip["id"], subject_person_id=world.driver.id)
    assert verified["accused_status"] == "verified_duty"  # the person the verified record puts on duty
    on_conductor = make(client, db, "conductor", trip_id=trip["id"], subject_person_id=world.conductor.id)
    assert on_conductor["accused_status"] == "verified_duty"
    elsewhere = make(client, db, "driver", trip_id=trip["id"], subject_person_id=other_driver.id)
    assert elsewhere["accused_status"] == "directory_only"  # a real person, but not established for this trip
    no_trip = make(client, db, "driver", subject_person_id=world.driver.id)
    assert no_trip["accused_status"] == "directory_only"  # no verified record, so no duty verification
    owner = make(client, db, "owner", subject_person_id=world.owner.id)
    assert owner["accused_status"] == "registered_owner"  # the owner on the vehicle record
    named = make(client, db, "driver", subject_person_text="Unknown driver")
    assert named["accused_status"] == "unidentified"


def test_the_client_cannot_claim_a_person_is_verified(client, db, world, complaint_lists):
    other_driver = Person(full_name="Somebody Else", person_type=PersonType.DRIVER)
    db.add(other_driver)
    db.commit()
    forged = make(
        client, db, "driver", subject_person_id=other_driver.id, accused_status="verified_duty", accused_verified=True
    )
    assert forged["accused_status"] == "directory_only"


def test_an_unverified_duty_leaves_the_accused_unidentified(client, db, world, complaint_lists):
    trip = publish_trip(world, driver_person_id=None, conductor_person_id=None)  # no duty record at all
    saved = make(client, db, "driver", trip_id=trip["id"], subject_person_text="The driver (name not known)")
    assert saved["duty"]["verification_status"] == "Unavailable"
    assert saved["accused_status"] == "unidentified" and saved["subject_person_id"] is None


# ---------------------------------------------------------------- My Complaints


def seed_each(client, db, world):
    make(client, db, "driver", subject_person_id=world.driver.id, subject="Reckless driving")
    make(client, db, "driver", subject_text=None, subject="Rude driver")
    make(client, db, "conductor", subject_person_id=world.conductor.id, subject="No ticket")
    make(client, db, "owner", subject_person_id=world.owner.id, subject="Bus not maintained")
    make(client, db, "bus_service", subject="Bus left early")
    make(client, db, "other", subject_person_text="A passer-by", subject="Other matter")
    make(client, db, None, subject="Not classified yet")


def listing(client, **params):
    page = client.get(COMPLAINTS, params=params)
    assert page.status_code == 200, page.text
    return page.json()


def test_my_complaints_filters_by_target_on_the_server(client, db, world):
    seed_each(client, db, world)
    subjects = lambda **p: {r["subject"] for r in listing(client, **p)["items"]}  # noqa: E731
    assert subjects(target="driver") == {"Reckless driving", "Rude driver"}
    assert subjects(target="conductor") == {"No ticket"}
    assert subjects(target="owner") == {"Bus not maintained"}
    assert subjects(target="bus_service") == {"Bus left early"}
    assert subjects(target="other") == {"Other matter"}
    assert subjects(target="unclassified") == {"Not classified yet"}
    assert len(subjects()) == 7
    assert client.get(COMPLAINTS, params={"target": "nonsense"}).status_code == 422


def test_the_target_tabs_carry_real_counts(client, db, world):
    seed_each(client, db, world)
    counts = listing(client)["target_counts"]
    assert counts == {"all": 7, "driver": 2, "conductor": 1, "owner": 1, "bus_service": 1, "other": 1, "unclassified": 1}
    narrowed = listing(client, search="driver")["target_counts"]  # the search narrows the counts too
    assert narrowed["all"] == 1 and narrowed["driver"] == 1 and narrowed["conductor"] == 0  # only "Rude driver"
    assert listing(client, target="driver")["counts"]["all"] == 2  # the status counts follow the target


def test_the_rows_show_the_target_the_accused_the_category_and_the_area(client, db, world, complaint_lists):
    category = db.scalar(select(ComplaintCategory))
    make(client, db, "driver", subject_person_id=world.driver.id, category_id=category.id, subject="Overcharged")
    row = listing(client, target="driver")["items"][0]
    assert (row["target_name"], row["accused_name"], row["category_name"]) == ("Driver", "Saman Kumara", "Overcharging")
    assert (row["vehicle_number"], row["area_name"], row["accused_status"]) == ("ND-7782", "Galle", "directory_only")
    assert row["editable"] is True and row["reference_number"] is None


def test_my_complaints_shows_only_what_this_officer_registered(client, db, world):
    make(client, db, "driver", subject="Mine")
    make_user(db, "second@sprpta.test", UserRole.L1, full_name="Second Officer")
    second = TestClient(app)
    sign_in(second, "second@sprpta.test")
    second.post(COMPLAINTS, json=body(db, "driver", subject="Theirs"))

    assert {r["subject"] for r in listing(client)["items"]} == {"Mine"}
    assert {r["subject"] for r in listing(client, scope="all")["items"]} == {"Mine", "Theirs"}  # the queue cards use this
    assert listing(client, target="driver")["total"] == 1
    assert client.get(COMPLAINTS, params={"scope": "everyone"}).status_code == 422


def test_the_target_filter_is_paged(client, db, world):
    for n in range(12):
        make(client, db, "driver", subject=f"Driver {n:02d}")
    make(client, db, "owner", subject="Owner one")
    first = listing(client, target="driver")
    assert first["total"] == 12 and len(first["items"]) == 10
    second = listing(client, target="driver", page=2)
    assert len(second["items"]) == 2 and second["page"] == 2
    assert listing(client, target="owner")["total"] == 1


def test_a_forwarded_complaint_stays_read_only_with_its_classification(client, db, world, complaint_lists):
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    from app.models import ComplaintMedium, RouteStand, Severity

    saved = make(
        client, db, "driver", subject_person_id=world.driver.id, medium_id=db.scalar(select(ComplaintMedium.id)),
        complaint_date="2026-01-02", route_stand_id=db.scalar(select(RouteStand.id)),
        category_id=db.scalar(select(ComplaintCategory.id)), severity_id=db.scalar(select(Severity.id)),
        complainant_name="Kamala", description="Asked for double",
    )
    assert client.post(f"{COMPLAINTS}/{saved['id']}/forward").status_code == 200
    changed = client.put(f"{COMPLAINTS}/{saved['id']}", json=body(db, "conductor"))
    assert changed.status_code == 409 and error_code(changed) == "not_editable"
    shown = client.get(f"{COMPLAINTS}/{saved['id']}").json()
    assert shown["target_code"] == "driver" and shown["subject_person_name"] == "Saman Kumara"
    row = listing(client, target="driver")["items"][0]
    assert row["editable"] is False and row["area_name"] == "Galle"  # the Level 2 area it went to


# ---------------------------------------------------------------- the dashboard


def test_the_dashboard_counts_this_officers_complaints_by_target(client, db, world):
    summary = lambda: client.get("/api/l1/dashboard").json()["by_target"]  # noqa: E731
    assert summary() == {"driver": 0, "conductor": 0, "owner": 0, "bus_service": 0, "other": 0, "unclassified": 0}

    seed_each(client, db, world)
    make_user(db, "second@sprpta.test", UserRole.L1, full_name="Second Officer")
    second = TestClient(app)
    sign_in(second, "second@sprpta.test")
    second.post(COMPLAINTS, json=body(db, "owner", subject="Not mine"))  # another officer's work is not counted

    assert summary() == {"driver": 2, "conductor": 1, "owner": 1, "bus_service": 1, "other": 1, "unclassified": 1}
    assert second.get("/api/l1/dashboard").json()["by_target"]["owner"] == 1


# ---------------------------------------------------------------- who may use it


def test_only_level_one_staff_may_read_the_lists_and_classify(client, db, world):
    for url in (f"{COMPLAINTS}/targets", f"{COMPLAINTS}/categories"):
        assert TestClient(app).get(url).status_code == 401
        assert world.admin.get(url).status_code == 403
    area = TestClient(app)
    make_user(db, "chair@sprpta.test", UserRole.L3)
    sign_in(area, "chair@sprpta.test")
    assert area.post(COMPLAINTS, json=body(db, "driver")).status_code == 403
    assert area.get(COMPLAINTS, params={"target": "driver"}).status_code == 403


# ---------------------------------------------------------------- the development sample data


def test_the_dev_sample_script_is_repeatable_marked_and_removable(client, db, world, complaint_lists, monkeypatch):
    from app.scripts import seed_dev_complaints as seed

    monkeypatch.setattr(seed, "check_environment", lambda: None)
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=world.area.id)
    publish_trip(world)

    seed.create(db)
    rows = db.scalars(select(Complaint).where(Complaint.client_request_id.like("dev-test-%"))).all()
    assert rows and all(r.subject.startswith("[DEV-TEST]") for r in rows)
    first = len(rows)
    codes = {db.get(ComplaintTargetType, r.target_type_id).code for r in rows if r.target_type_id}
    assert {"driver", "conductor", "owner", "bus_service", "other"} <= codes  # every target is covered
    assert all(p.team_label == "DEV-TEST-DATA" for p in db.scalars(select(Person).where(Person.full_name.like("Test %Demo"))))

    seed.create(db)  # a second run adds nothing
    assert len(db.scalars(select(Complaint).where(Complaint.client_request_id.like("dev-test-%"))).all()) == first
    summary = client.get(f"{COMPLAINTS}", params={"scope": "all", "target": "driver"}).json()
    assert summary["total"] >= 1

    seed.remove(db)
    assert db.scalars(select(Complaint).where(Complaint.client_request_id.like("dev-test-%"))).all() == []
    assert db.scalars(select(Person).where(Person.team_label == "DEV-TEST-DATA")).all() == []


def test_the_dev_sample_script_refuses_to_run_outside_development(monkeypatch):
    from app.scripts import seed_dev_complaints as seed

    monkeypatch.setattr(seed.settings, "app_env", "production")
    with pytest.raises(SystemExit):
        seed.check_environment()
    monkeypatch.setattr(seed.settings, "app_env", "development")
    monkeypatch.setattr(seed.settings, "database_url", "postgresql+psycopg://u:p@db.example.com:5432/x")
    with pytest.raises(SystemExit):
        seed.check_environment()
