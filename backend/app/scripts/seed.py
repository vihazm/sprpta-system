"""Seed reference data and the first accounts. Safe to run repeatedly.

    cd backend
    .venv\\Scripts\\python -m app.scripts.seed

- Always: the three areas (DB doc 5.7).
- Development only (APP_ENV=development): one demo account per role, so every
  role's redirect can be tried. Logins are emails, as the documents require.
- Production: one admin from ADMIN_LOGIN / ADMIN_PASSWORD / ADMIN_NAME (set in
  the environment, never committed). The password is not defined by the
  documents ([OPEN] in the UI Flow doc), so it comes from the environment.
"""

import os
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identifiers import normalise_identifier
from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Area, ComplainantAccount, User

AREAS = ["Galle", "Matara", "Hambantota"]

# DEVELOPMENT ONLY. These credentials are public in the repository; they are
# never created when APP_ENV is not "development".
DEV_STAFF = [
    # (full name, login, role, area, password)
    ("Test Chairman", "test_chairman@sprpta.test", UserRole.L3, None, "chairman123"),
    ("Test Area Officer (Galle)", "test_ad_galle@sprpta.test", UserRole.L2, "Galle", "ad_galle123"),
    ("Test Office Staff", "test_office@sprpta.test", UserRole.L1, None, "office123"),
    ("System Admin", "system_admin@sprpta.test", UserRole.ADMIN, None, "admin123"),
    ("Test Ground Staff", "test_groundstaff@sprpta.test", UserRole.IMPLEMENTING_STAFF, None, "groundstaff123"),
]
DEV_COMPLAINANTS = [
    # (display name, email, password)
    ("Test Client", "test_client1@sprpta.test", "client1abc"),
]


def _area_ids(db: Session) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name in AREAS:
        area = db.scalar(select(Area).where(Area.name == name))
        if area is None:
            area = Area(name=name)
            db.add(area)
            db.flush()
            print(f"  created area {name}")
        ids[name] = area.id
    return ids


def _ensure_staff(db: Session, name: str, login: str, role: UserRole, area_id: int | None, password: str) -> None:
    parsed = normalise_identifier(login)
    if parsed is None:
        raise SystemExit(f"Not a valid email or Sri Lankan mobile number: {login!r}")
    login = parsed[1]
    if db.scalar(select(User).where(User.login == login)) is not None:
        print(f"  exists  {login} ({role.value})")
        return
    db.add(User(full_name=name, login=login, password_hash=hash_password(password), role=role, area_id=area_id))
    print(f"  created {login} ({role.value})")


def main() -> None:
    with SessionLocal() as db:
        print("Areas")
        areas = _area_ids(db)

        if settings.is_development:
            print("Development accounts")
            for name, login, role, area, password in DEV_STAFF:
                _ensure_staff(db, name, login, role, areas[area] if area else None, password)
            for name, email, password in DEV_COMPLAINANTS:
                if db.scalar(select(ComplainantAccount).where(ComplainantAccount.email == email)) is None:
                    db.add(
                        ComplainantAccount(
                            display_name=name,
                            email=email,
                            password_hash=hash_password(password),
                            verified_at=datetime.now(UTC),
                        )
                    )
                    print(f"  created {email} (cp)")
                else:
                    print(f"  exists  {email} (cp)")
        else:
            login, password = os.environ.get("ADMIN_LOGIN"), os.environ.get("ADMIN_PASSWORD")
            if not login or not password:
                raise SystemExit("Set ADMIN_LOGIN and ADMIN_PASSWORD to create the first admin.")
            print("Administrator")
            _ensure_staff(db, os.environ.get("ADMIN_NAME", "System Administrator"), login,
                          UserRole.ADMIN, None, password)
        db.commit()
    print("Done.")


if __name__ == "__main__":
    main()
