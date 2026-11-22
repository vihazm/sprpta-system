from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.enums import PersonType, VehicleType
from app.core.roles import UserRole
from app.models import AuditLog, ComplaintCategory, ComplaintMedium, Person, Severity, Vehicle
from tests.conftest import make_user, sign_in

URL = "/api/admin/master-data"


@pytest.fixture
def admin(db, client):
    user = make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="Sarah Admin")
    sign_in(client, "admin@sprpta.test")
    return user


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def add(client, entity: str, **values):
    return client.post(f"{URL}/{entity}", json={"values": values})


def edit(client, entity: str, record_id: int, *, active: bool = True, **values):
    return client.put(f"{URL}/{entity}/{record_id}", json={"values": values, "is_active": active})


def audit_rows(db) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))


# ---------------------------------------------------------------- access


def test_only_the_admin_may_use_master_data(client, db):
    assert client.get(URL).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}/vehicles").status_code == 403
    assert add(client, "areas", name="Galle").status_code == 403


def test_unknown_kinds_and_records_are_turned_away(client, db, admin):
    assert client.get(f"{URL}/buses").status_code == 422
    assert edit(client, "areas", 999, name="Galle").status_code == 404


# ---------------------------------------------------------------- reading


def test_the_hub_counts_every_kind(client, db, admin, galle):
    db.add(ComplaintCategory(name="Overcharging", is_active=False))
    db.commit()
    counts = {row["key"]: row for row in client.get(URL).json()}
    assert list(counts) == ["areas", "routes", "vehicles", "permits", "people", "categories", "severities", "mediums"]
    assert counts["areas"] == {"key": "areas", "total": 1, "active": 1}
    assert counts["categories"] == {"key": "categories", "total": 1, "active": 0}


def test_the_list_searches_filters_pages_and_shows_names(client, db, admin, galle):
    owner = Person(full_name="Nimal Perera", person_type=PersonType.OWNER)
    db.add(owner)
    db.flush()
    db.add_all(
        [
            Vehicle(vehicle_number=f"NA-{n:04d}", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
            for n in range(12)
        ]
        + [
            Vehicle(vehicle_number="NB-5555", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, owner_person_id=owner.id),
            Vehicle(vehicle_number="NC-9999", vehicle_type=VehicleType.TRISHAW, registered_area_id=galle.id, is_active=False),
        ]
    )
    db.commit()

    page = client.get(f"{URL}/vehicles").json()
    assert page["total"] == 14 and page["page_size"] == 10 and len(page["items"]) == 10
    assert page["counts"] == {"all": 14, "active": 13, "inactive": 1}
    assert len(client.get(f"{URL}/vehicles", params={"page": 2}).json()["items"]) == 4

    found = client.get(f"{URL}/vehicles", params={"search": "perera"}).json()["items"]
    assert [(v["vehicle_number"], v["owner_name"], v["area_name"]) for v in found] == [("NB-5555", "Nimal Perera", "Galle")]
    inactive = client.get(f"{URL}/vehicles", params={"status": "inactive"}).json()["items"]
    assert [v["vehicle_number"] for v in inactive] == ["NC-9999"]


# ---------------------------------------------------------------- adding and editing


def test_adding_a_vehicle_tidies_the_number_and_is_audited(client, db, admin, galle):
    response = add(client, "vehicles", vehicle_number="  na   1234 ", vehicle_type="bus", registered_area_id=galle.id)
    assert response.status_code == 201
    vehicle = response.json()
    assert vehicle["vehicle_number"] == "NA 1234" and vehicle["area_name"] == "Galle" and vehicle["is_active"]

    [entry] = audit_rows(db)
    assert (entry.action, entry.entity_type, entry.entity_id, entry.actor_user_id) == (
        "master_data.create", "vehicles", vehicle["id"], admin.id,
    )
    assert entry.details["changes"]["vehicle_number"] == [None, "NA 1234"]


def test_a_vehicle_needs_a_registered_area_and_a_new_number(client, db, admin, galle):
    assert add(client, "vehicles", vehicle_number="NA-1234", vehicle_type="bus").status_code == 422
    galle.is_active = False
    db.commit()
    missing_area = add(client, "vehicles", vehicle_number="NA-1234", vehicle_type="bus", registered_area_id=galle.id)
    assert error_code(missing_area) == "not_found"

    galle.is_active = True
    db.commit()
    assert add(client, "vehicles", vehicle_number="NA-1234", vehicle_type="bus", registered_area_id=galle.id).status_code == 201
    # L1 matches numbers ignoring spaces and dashes, so this is the same bus.
    same = add(client, "vehicles", vehicle_number="NA 1234", vehicle_type="bus", registered_area_id=galle.id)
    assert same.status_code == 409 and error_code(same) == "already_exists"


def test_a_duplicate_name_and_an_unknown_field_are_refused(client, db, admin):
    assert add(client, "categories", name="Overcharging").status_code == 201
    assert error_code(add(client, "categories", name="Overcharging")) == "already_exists"
    assert add(client, "categories", name="Rude staff", colour="red").status_code == 422
    assert add(client, "categories", name="   ").status_code == 422
    assert add(client, "categories", name="Bad\x00name").status_code == 422


def test_editing_records_only_what_changed_and_deactivates_without_deleting(client, db, admin):
    person = add(client, "people", full_name="Sunil Silva", person_type="driver", phone=" ").json()
    assert person["phone"] is None  # a blank optional field is stored as empty

    changed = edit(client, "people", person["id"], active=False, full_name="Sunil Silva", person_type="conductor")
    assert changed.status_code == 200 and changed.json()["is_active"] is False
    update = audit_rows(db)[-1]
    assert update.action == "master_data.update"
    assert update.details["changes"] == {"person_type": ["driver", "conductor"], "is_active": [True, False]}

    # Saving without a change writes nothing.
    before = len(audit_rows(db))
    edit(client, "people", person["id"], active=False, full_name="Sunil Silva", person_type="conductor")
    assert len(audit_rows(db)) == before
    assert db.get(Person, person["id"]) is not None


def test_an_area_in_use_cannot_be_deactivated(client, db, admin, galle):
    make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=galle.id)
    refused = edit(client, "areas", galle.id, active=False, name="Galle")
    assert refused.status_code == 409 and error_code(refused) == "area_in_use"
    assert edit(client, "areas", galle.id, name="Galle District").json()["name"] == "Galle District"


def test_severities_can_only_be_renamed(client, db, admin):
    severity = Severity(name="Critical", rank=1, forward_days=0, decide_days=1, close_days=3, rating_weight=Decimal(8))
    db.add(severity)
    db.commit()
    assert error_code(add(client, "severities", name="Urgent")) == "fixed_list"
    assert error_code(edit(client, "severities", severity.id, active=False, name="Critical")) == "fixed_list"
    renamed = edit(client, "severities", severity.id, name="Very urgent").json()
    assert (renamed["name"], renamed["rank"]) == ("Very urgent", 1)
    # The time targets belong to Settings and cannot be sent here.
    assert edit(client, "severities", severity.id, name="Critical", decide_days=5).status_code == 422


def test_the_portal_medium_cannot_be_changed(client, db, admin):
    portal = ComplaintMedium(name="Portal", is_system=True)
    db.add(portal)
    db.commit()
    assert error_code(edit(client, "mediums", portal.id, active=False, name="Portal")) == "system_medium"
    assert error_code(edit(client, "mediums", portal.id, name="Website")) == "system_medium"
    assert add(client, "mediums", name="Fax").status_code == 201
