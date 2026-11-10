"""Staff accounts for the administrator's Users page (UI-AD-02).

Reading is done by the database (filtering, counting, paging). Creating and
editing enforce the rules the database cannot explain in words: a login is
unique across staff and complainants, a Level 2 officer needs a free area, and
administrators cannot deactivate themselves or change their own role.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, distinct, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.identifiers import normalise_identifier
from app.core.roles import UserRole
from app.core.security import hash_password
from app.models import Area, AuthSession, ComplainantAccount, User
from app.schemas.admin_users import (
    AreaCoverage,
    NewUser,
    UserChanges,
    UserFields,
    UserList,
    UserOut,
    UsersSummary,
)

PAGE_SIZE = 10


class UserError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------------------------------------------------------- reading


def _live_session(now: datetime):
    """A session counts as live until it is revoked or runs out of time."""
    return (
        AuthSession.revoked_at.is_(None),
        AuthSession.idle_expires_at > now,
        AuthSession.absolute_expires_at > now,
    )


def _rows(now: datetime):
    signed_in = exists().where(AuthSession.user_id == User.id, *_live_session(now))
    return select(User, Area.name, signed_in).outerjoin(Area, Area.id == User.area_id)


def _status_of(user: User, now: datetime) -> str:
    if not user.is_active:
        return "inactive"
    return "locked" if user.locked_until and user.locked_until > now else "active"


def _out(row, now: datetime) -> UserOut:
    user, area_name, signed_in = row
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        login=user.login,
        role=user.role,
        area_id=user.area_id,
        area_name=area_name,
        status=_status_of(user, now),
        signed_in=signed_in,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _status_condition(status: str, now: datetime):
    if status == "active":
        return User.is_active
    if status == "inactive":
        return User.is_active.is_(False)
    return and_(User.is_active, User.locked_until > now)


def list_users(
    db: Session, *, search: str, status: str | None, role: UserRole | None, page: int
) -> UserList:
    now = datetime.now(UTC)
    conditions = []
    term = search.strip()
    if term:
        # Phone numbers are stored without spaces, so spaces are ignored when matching a login.
        conditions.append(
            or_(
                User.full_name.icontains(term, autoescape=True),
                User.login.icontains(term.replace(" ", ""), autoescape=True),
            )
        )
    if status:
        conditions.append(_status_condition(status, now))

    by_role = dict(db.execute(select(User.role, func.count()).where(*conditions).group_by(User.role)).all())
    role_counts = {"all": sum(by_role.values()), **{r.value: by_role.get(r, 0) for r in UserRole}}

    shown = [*conditions, User.role == role] if role else conditions
    total = db.scalar(select(func.count()).select_from(User).where(*shown)) or 0
    page = min(page, max(1, -(-total // PAGE_SIZE)))  # a page past the end shows the last one
    rows = db.execute(
        _rows(now)
        .where(*shown)
        .order_by(User.role, User.full_name, User.id)  # roles in their usual order, then by name
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()

    return UserList(
        items=[_out(row, now) for row in rows],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        role_counts=role_counts,
    )


def get_user(db: Session, user_id: int) -> UserOut:
    now = datetime.now(UTC)
    row = db.execute(_rows(now).where(User.id == user_id)).one_or_none()
    if row is None:
        raise UserError(404, "not_found", "That user does not exist.")
    return _out(row, now)


def summary(db: Session) -> UsersSummary:
    now = datetime.now(UTC)
    by_role = dict(db.execute(select(User.role, func.count()).where(User.is_active).group_by(User.role)).all())

    signed_in = db.scalar(
        select(func.count(distinct(AuthSession.user_id))).where(AuthSession.user_id.is_not(None), *_live_session(now))
    )
    locked = db.scalar(select(func.count()).select_from(User).where(_status_condition("locked", now)))
    inactive = db.scalar(select(func.count()).select_from(User).where(_status_condition("inactive", now)))

    officers = db.execute(
        select(Area.id, Area.name, User.id, User.full_name)
        .outerjoin(User, and_(User.area_id == Area.id, User.role == UserRole.L2, User.is_active))
        .where(Area.is_active)
        .order_by(Area.id)
    ).all()

    return UsersSummary(
        active=sum(by_role.values()),
        signed_in_now=signed_in or 0,
        locked=locked or 0,
        inactive=inactive or 0,
        by_role={r.value: by_role.get(r, 0) for r in UserRole},
        areas=[
            AreaCoverage(id=area_id, name=area_name, officer_id=officer_id, officer_name=officer_name)
            for area_id, area_name, officer_id, officer_name in officers
        ],
    )


# ---------------------------------------------------------------- changing


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        # The checks below catch the normal cases; this is two people saving at once.
        db.rollback()
        raise UserError(409, "conflict", "This was just changed by someone else. Refresh and try again.") from None


def _checked_login_and_area(
    db: Session, data: UserFields, *, user: User | None, active: bool
) -> tuple[str, int | None]:
    """Check the login and area against the rules. Returns the login to store and the area id."""
    parsed = normalise_identifier(data.login)
    if parsed is None:
        raise UserError(422, "invalid_login", "Enter a valid email address or a Sri Lankan mobile number.")
    login = parsed[1]

    own_id = user.id if user else None
    in_staff = db.scalar(select(User.id).where(User.login == login, User.id != own_id))
    in_portal = db.scalar(
        select(ComplainantAccount.id).where(or_(ComplainantAccount.email == login, ComplainantAccount.phone == login))
    )
    if in_staff or in_portal:
        raise UserError(409, "login_taken", "That email or phone number is already used by another account.")

    if data.role != UserRole.L2:
        return login, None

    area = db.get(Area, data.area_id) if data.area_id else None
    if area is None or not area.is_active:
        raise UserError(422, "area_required", "Choose an area for a Level 2 officer.")
    if active:
        officer = db.scalar(
            select(User.id).where(User.role == UserRole.L2, User.is_active, User.area_id == area.id, User.id != own_id)
        )
        if officer:
            raise UserError(409, "area_taken", f"{area.name} already has an active Level 2 officer.")
    return login, area.id


def create_user(db: Session, admin_id: int, data: NewUser) -> UserOut:
    login, area_id = _checked_login_and_area(db, data, user=None, active=True)
    user = User(
        full_name=data.full_name.strip(),
        login=login,
        password_hash=hash_password(data.password),
        role=data.role,
        area_id=area_id,
        created_by=admin_id,
    )
    db.add(user)
    _commit(db)
    return get_user(db, user.id)


def _find(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserError(404, "not_found", "That user does not exist.")
    return user


def update_user(db: Session, admin_id: int, user_id: int, data: UserChanges) -> UserOut:
    user = _find(db, user_id)
    login, area_id = _checked_login_and_area(db, data, user=user, active=data.is_active)

    # Only an active administrator gets here, so refusing these two changes to your own account
    # also guarantees that at least one administrator always stays active.
    if user.id == admin_id:
        if not data.is_active:
            raise UserError(409, "cannot_deactivate_self", "You cannot deactivate your own account.")
        if data.role != user.role:
            raise UserError(409, "cannot_change_own_role", "You cannot change your own role.")

    if user.is_active and not data.is_active:
        # Switching someone off ends their sessions at once.
        db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC), revoke_reason="deactivated")
        )

    user.full_name = data.full_name.strip()
    user.login = login
    user.role = data.role
    user.area_id = area_id
    user.is_active = data.is_active
    _commit(db)
    return get_user(db, user.id)


def unlock_user(db: Session, user_id: int) -> UserOut:
    user = _find(db, user_id)
    user.locked_until = None
    user.failed_login_count = 0
    _commit(db)
    return get_user(db, user.id)
