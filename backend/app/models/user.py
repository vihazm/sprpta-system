from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import UserRole
from app.db.base import Base


class User(Base):
    """DB doc 2.1: staff accounts (L1, L2, L3, Admin, implementing staff).

    Created by Admin only. `login` is the email or phone used on the common
    login page, stored in normalised form (see app.core.identifiers).
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role <> 'l2' OR area_id IS NOT NULL", name="l2_needs_area"),
        # One active L2 officer per area, so forwarding by area finds exactly
        # one officer (DB doc 2.1, open item 2).
        Index(
            "uq_users_one_active_l2_per_area",
            "area_id",
            unique=True,
            postgresql_where=text("role = 'l2' AND is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    login: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e])
    )
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    failed_login_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
