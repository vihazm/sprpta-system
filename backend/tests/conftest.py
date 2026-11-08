"""Test setup: a separate `sprpta_test` database, built with the real migrations.

The development database is never touched: DATABASE_URL is redirected before
the app is imported.
"""

import os
from pathlib import Path

import psycopg
import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

# IMPORTANT: nothing from `app` may be imported above the os.environ lines below,
# because app.core.config reads DATABASE_URL once, at import time.
_dev_url = os.environ.get("DATABASE_URL") or dotenv_values(
    Path(__file__).resolve().parents[1] / ".env"
).get("DATABASE_URL")
if not _dev_url:
    raise RuntimeError("Set DATABASE_URL in backend/.env so the tests can find the server.")
_base = make_url(_dev_url)
_test_url = _base.set(database="sprpta_test")
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 40)
os.environ["APP_ENV"] = "development"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.rate_limit import login_failures  # noqa: E402
from app.core.roles import UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Area, ComplainantAccount, User  # noqa: E402

PASSWORD = "correct-horse-1"


def _admin_dsn(dbname: str) -> str:
    return _base.set(drivername="postgresql", database=dbname).render_as_string(hide_password=False)


@pytest.fixture(scope="session", autouse=True)
def _database():
    # Safety net: never let a test run wipe anything but the test database.
    from app.core.config import settings

    assert make_url(settings.database_url).database == "sprpta_test", settings.database_url
    with psycopg.connect(_admin_dsn("postgres"), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname='sprpta_test'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE sprpta_test")
    with SessionLocal() as db:
        db.execute(text("DROP SCHEMA public CASCADE"))
        db.execute(text("CREATE SCHEMA public"))
        db.commit()
    command.upgrade(Config("alembic.ini"), "head")  # also proves the migration works
    yield


@pytest.fixture(autouse=True)
def _clean():
    login_failures.reset()
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE usage_logs, auth_sessions, users, complainant_accounts, areas "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def galle(db) -> Area:
    area = Area(name="Galle")
    db.add(area)
    db.commit()
    return area


def make_user(db, login: str, role: UserRole, *, area_id=None, **extra) -> User:
    user = User(
        full_name=f"Test {role.value}",
        login=login,
        password_hash=hash_password(PASSWORD),
        role=role,
        area_id=area_id,
        **extra,
    )
    db.add(user)
    db.commit()
    return user


def make_complainant(db, email: str, **extra) -> ComplainantAccount:
    from datetime import UTC, datetime

    extra.setdefault("verified_at", datetime.now(UTC))
    account = ComplainantAccount(
        email=email, display_name="Test Client", password_hash=hash_password(PASSWORD), **extra
    )
    db.add(account)
    db.commit()
    return account


def sign_in(client: TestClient, identifier: str, password: str = PASSWORD, **headers):
    return client.post(
        "/api/auth/login", json={"identifier": identifier, "password": password}, headers=headers
    )
