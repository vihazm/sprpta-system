"""Request and response shapes of the administrator's Users page (UI-AD-02)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.core.roles import UserRole


def _reject_nul(text: str) -> str:
    # The database cannot store a NUL character, so turn it away here as a normal 422.
    if "\x00" in text:
        raise ValueError("must not contain a NUL character")
    return text


NoNul = AfterValidator(_reject_nul)

# Ids are 64-bit in the database; anything larger would crash the query, so it is turned away as a 422.
MAX_ID = 2**63 - 1

# Inactive means deactivated. Locked is an active account that is waiting out a lockout.
Status = Literal["active", "locked", "inactive"]


class UserFields(BaseModel):
    """What an administrator can set on a staff account."""

    full_name: Annotated[str, NoNul] = Field(min_length=1, max_length=120, pattern=r"\S")
    login: Annotated[str, NoNul] = Field(min_length=1, max_length=254)  # an email address or a phone number
    role: UserRole
    area_id: int | None = Field(default=None, ge=1, le=MAX_ID)  # required for Level 2 officers, ignored for everyone else


class NewUser(UserFields):
    password: str = Field(min_length=8, max_length=128)


class UserChanges(UserFields):
    is_active: bool


class UserOut(BaseModel):
    id: int
    full_name: str
    login: str
    role: UserRole
    area_id: int | None
    area_name: str | None
    status: Status
    signed_in: bool  # has a live session right now
    last_login_at: datetime | None
    created_at: datetime


class UserList(BaseModel):
    items: list[UserOut]
    total: int  # matching the search, status and role
    page: int
    page_size: int
    role_counts: dict[str, int]  # matching the search and status, per role, plus "all"


class AreaCoverage(BaseModel):
    id: int
    name: str
    officer_id: int | None  # the active Level 2 officer, if there is one
    officer_name: str | None


class UsersSummary(BaseModel):
    active: int  # includes locked accounts
    signed_in_now: int
    locked: int
    inactive: int
    by_role: dict[str, int]  # active staff per role
    areas: list[AreaCoverage]
