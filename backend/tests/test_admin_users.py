from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.roles import UserRole
from app.main import app
from app.models import Area, User
from tests.conftest import PASSWORD, make_complainant, make_user, sign_in

URL = "/api/admin/users"


def signed_in_admin(db, client) -> User:
    admin = make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="Sarah Admin")
    sign_in(client, "admin@sprpta.test")
    return admin


def new_user(**changes) -> dict:
    body = {
        "full_name": "Kavindu Perera",
        "login": "kavindu@sprpta.test",
        "password": "first-password-1",
        "role": "l1",
        "area_id": None,
    }
    return {**body, **changes}


def edit_body(user: User, **changes) -> dict:
    body = {
        "full_name": user.full_name,
        "login": user.login,
        "role": user.role.value,
        "area_id": user.area_id,
        "is_active": user.is_active,
    }
    return {**body, **changes}


def error_code(response) -> str:
    return response.json()["detail"]["code"]


# ---------------------------------------------------------------- access


def test_only_the_admin_may_use_the_users_api(client, db):
    assert client.get(URL).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}/summary").status_code == 403
    assert client.post(URL, json=new_user()).status_code == 403


# ---------------------------------------------------------------- reading


def test_list_filters_by_search_status_and_role(client, db, galle):
    signed_in_admin(db, client)
    make_user(db, "kavindu@sprpta.test", UserRole.L1, full_name="Kavindu Perera")
    make_user(db, "+94712345601", UserRole.L1, full_name="Nimali Fernando")
    make_user(db, "ruwan@sprpta.test", UserRole.L2, full_name="Ruwan Silva", area_id=galle.id)
    make_user(db, "gone@sprpta.test", UserRole.L1, full_name="Chamara Bandara", is_active=False)
    make_user(
        db, "locked@sprpta.test", UserRole.IMPLEMENTING_STAFF,
        full_name="Lakmal Herath", locked_until=datetime.now(UTC) + timedelta(minutes=10),
    )

    def names(**params) -> list[str]:
        return [u["full_name"] for u in client.get(URL, params=params).json()["items"]]

    assert len(names()) == 6
    assert names(search="kavin") == ["Kavindu Perera"]
    assert names(search="+94 71 234 5601") == ["Nimali Fernando"]  # spaces in what is typed are ignored
    assert names(status="inactive") == ["Chamara Bandara"]
    assert names(status="locked") == ["Lakmal Herath"]
    assert len(names(status="active")) == 5  # a locked account is still active
    assert names(role="l2") == ["Ruwan Silva"]


def test_role_counts_follow_search_and_status_but_not_the_role_filter(client, db):
    signed_in_admin(db, client)
    make_user(db, "a@sprpta.test", UserRole.L1, full_name="Alex One")
    make_user(db, "b@sprpta.test", UserRole.L1, full_name="Alex Two")
    make_user(db, "c@sprpta.test", UserRole.L3, full_name="Chair Person")

    body = client.get(URL, params={"search": "alex", "role": "l3"}).json()
    assert body["total"] == 0
    assert body["role_counts"] == {"all": 2, "l1": 2, "l2": 0, "l3": 0, "admin": 0, "implementing_staff": 0}


def test_list_is_paged_and_roles_come_in_their_usual_order(client, db):
    signed_in_admin(db, client)
    for i in range(12):
        make_user(db, f"user{i:02}@sprpta.test", UserRole.L1, full_name=f"Person {i:02}")

    first = client.get(URL).json()
    second = client.get(URL, params={"page": 2}).json()
    assert (first["total"], first["page_size"], len(first["items"]), len(second["items"])) == (13, 10, 10, 3)
    assert second["items"][-1]["role"] == "admin"  # L1 staff first, the administrator last
    assert client.get(URL, params={"page": 9}).json()["page"] == 2  # past the end shows the last page


def test_list_shows_sign_in_and_status_details(client, db):
    signed_in_admin(db, client)
    make_user(db, "kavindu@sprpta.test", UserRole.L1, full_name="Kavindu Perera")
    sign_in(TestClient(app), "kavindu@sprpta.test")

    by_name = {u["full_name"]: u for u in client.get(URL).json()["items"]}
    assert by_name["Kavindu Perera"]["signed_in"] is True
    assert by_name["Kavindu Perera"]["last_login_at"] is not None
    assert "password_hash" not in client.get(URL).text


def test_summary_counts_and_area_coverage(client, db, galle):
    signed_in_admin(db, client)
    matara = Area(name="Matara")
    db.add(matara)
    db.commit()
    make_user(db, "ruwan@sprpta.test", UserRole.L2, full_name="Ruwan Silva", area_id=galle.id)
    make_user(db, "old@sprpta.test", UserRole.L2, full_name="Old Officer", area_id=matara.id, is_active=False)
    make_user(db, "gone@sprpta.test", UserRole.L1, is_active=False)
    make_user(
        db, "locked@sprpta.test", UserRole.L1, locked_until=datetime.now(UTC) + timedelta(minutes=10)
    )
    sign_in(TestClient(app), "ruwan@sprpta.test")

    body = client.get(f"{URL}/summary").json()
    assert (body["active"], body["signed_in_now"], body["locked"], body["inactive"]) == (3, 2, 1, 2)
    assert body["by_role"] == {"l1": 1, "l2": 1, "l3": 0, "admin": 1, "implementing_staff": 0}
    assert [(a["name"], a["officer_name"]) for a in body["areas"]] == [("Galle", "Ruwan Silva"), ("Matara", None)]


# ---------------------------------------------------------------- creating


def test_a_new_user_can_sign_in_with_the_password_the_admin_set(client, db):
    admin = signed_in_admin(db, client)

    response = client.post(URL, json=new_user(login=" Kavindu@SPRPTA.test "))
    assert response.status_code == 201
    assert response.json()["login"] == "kavindu@sprpta.test"  # stored in normalised form
    assert sign_in(TestClient(app), "kavindu@sprpta.test", "first-password-1").status_code == 200
    assert db.query(User).filter_by(login="kavindu@sprpta.test").one().created_by == admin.id


def test_phone_logins_are_normalised(client, db):
    signed_in_admin(db, client)
    response = client.post(URL, json=new_user(login="071 234 5601"))
    assert response.json()["login"] == "+94712345601"


def test_a_login_cannot_be_reused_by_staff_or_complainants(client, db):
    signed_in_admin(db, client)
    make_complainant(db, "portal@sprpta.test")

    assert error_code(client.post(URL, json=new_user(login="admin@sprpta.test"))) == "login_taken"
    assert error_code(client.post(URL, json=new_user(login="portal@sprpta.test"))) == "login_taken"
    assert error_code(client.post(URL, json=new_user(login="not a login"))) == "invalid_login"


def test_a_level_2_officer_needs_a_free_area(client, db, galle):
    signed_in_admin(db, client)

    assert error_code(client.post(URL, json=new_user(role="l2"))) == "area_required"
    assert client.post(URL, json=new_user(role="l2", area_id=galle.id)).status_code == 201

    second = client.post(URL, json=new_user(login="two@sprpta.test", role="l2", area_id=galle.id))
    assert (second.status_code, error_code(second)) == (409, "area_taken")


def test_other_roles_do_not_keep_an_area(client, db, galle):
    signed_in_admin(db, client)
    response = client.post(URL, json=new_user(role="l1", area_id=galle.id))
    assert response.json()["area_id"] is None


def test_a_short_password_is_refused(client, db):
    signed_in_admin(db, client)
    assert client.post(URL, json=new_user(password="short")).status_code == 422


# ---------------------------------------------------------------- editing


def test_editing_changes_name_login_role_and_area(client, db, galle):
    signed_in_admin(db, client)
    user = make_user(db, "kavindu@sprpta.test", UserRole.L1, full_name="Kavindu Perera")

    response = client.put(
        f"{URL}/{user.id}", json=edit_body(user, full_name="Kavindu P", login="0771234567", role="l2", area_id=galle.id)
    )
    body = response.json()
    assert (body["full_name"], body["login"], body["role"], body["area_name"]) == (
        "Kavindu P", "+94771234567", "l2", "Galle",
    )


def test_deactivating_ends_the_persons_sessions_at_once(client, db):
    signed_in_admin(db, client)
    user = make_user(db, "kavindu@sprpta.test", UserRole.L1)
    other = TestClient(app)
    sign_in(other, "kavindu@sprpta.test")
    assert other.get("/api/auth/me").status_code == 200

    response = client.put(f"{URL}/{user.id}", json=edit_body(user, is_active=False))
    assert response.json()["status"] == "inactive"
    assert other.get("/api/auth/me").status_code == 401
    assert client.get(f"{URL}/summary").json()["signed_in_now"] == 1


def test_an_admin_cannot_deactivate_themselves(client, db):
    admin = signed_in_admin(db, client)
    make_user(db, "second@sprpta.test", UserRole.ADMIN)

    response = client.put(f"{URL}/{admin.id}", json=edit_body(admin, is_active=False))
    assert (response.status_code, error_code(response)) == (409, "cannot_deactivate_self")


def test_an_admin_cannot_change_their_own_role(client, db):
    admin = signed_in_admin(db, client)
    make_user(db, "second@sprpta.test", UserRole.ADMIN)

    response = client.put(f"{URL}/{admin.id}", json=edit_body(admin, role="l1"))
    assert (response.status_code, error_code(response)) == (409, "cannot_change_own_role")
    assert client.get(URL).status_code == 200  # still an administrator


def test_an_admin_can_still_edit_themselves_and_demote_other_admins(client, db):
    admin = signed_in_admin(db, client)
    other = make_user(db, "second@sprpta.test", UserRole.ADMIN)

    assert client.put(f"{URL}/{admin.id}", json=edit_body(admin, full_name="Sarah A")).status_code == 200
    assert client.put(f"{URL}/{other.id}", json=edit_body(other, role="l1")).status_code == 200
    assert client.put(f"{URL}/{other.id}", json=edit_body(other, role="l1", is_active=False)).status_code == 200


def test_reactivating_a_level_2_officer_needs_the_area_to_be_free(client, db, galle):
    signed_in_admin(db, client)
    old = make_user(db, "old@sprpta.test", UserRole.L2, area_id=galle.id, is_active=False)
    make_user(db, "new@sprpta.test", UserRole.L2, area_id=galle.id)

    response = client.put(f"{URL}/{old.id}", json=edit_body(old, is_active=True))
    assert (response.status_code, error_code(response)) == (409, "area_taken")


def test_editing_an_unknown_user_is_not_found(client, db):
    signed_in_admin(db, client)
    ghost = User(full_name="Ghost", login="ghost@sprpta.test", role=UserRole.L1, area_id=None, is_active=True)
    assert client.put(f"{URL}/9999", json=edit_body(ghost)).status_code == 404
    assert client.post(f"{URL}/9999/unlock").status_code == 404


# ---------------------------------------------------------------- unlocking


def test_unlocking_lets_the_person_sign_in_again(client, db):
    signed_in_admin(db, client)
    user = make_user(
        db, "kavindu@sprpta.test", UserRole.L1,
        locked_until=datetime.now(UTC) + timedelta(minutes=10), failed_login_count=3,
    )
    assert sign_in(TestClient(app), "kavindu@sprpta.test", PASSWORD).status_code == 423

    response = client.post(f"{URL}/{user.id}/unlock")
    assert response.json()["status"] == "active"
    assert sign_in(TestClient(app), "kavindu@sprpta.test", PASSWORD).status_code == 200


def test_a_nul_character_is_refused_instead_of_crashing(client, db):
    signed_in_admin(db, client)

    assert client.get(URL, params={"search": "a\x00b"}).status_code == 422
    assert client.post(URL, json=new_user(full_name="Bad\x00Name")).status_code == 422
    assert client.post(URL, json=new_user(login="a\x00b@sprpta.test")).status_code == 422


def test_ids_too_big_for_the_database_are_refused_instead_of_crashing(client, db):
    admin = signed_in_admin(db, client)
    too_big = 2**63

    assert client.put(f"{URL}/{too_big}", json=edit_body(admin)).status_code == 422
    assert client.post(f"{URL}/{too_big}/unlock").status_code == 422
    assert client.post(URL, json=new_user(role="l2", area_id=too_big)).status_code == 422
    assert client.post(URL, json=new_user(area_id=too_big)).status_code == 422
