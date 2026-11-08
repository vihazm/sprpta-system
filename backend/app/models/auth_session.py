from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthSession(Base):
    """A login session (proposed in DB doc 5.8, "session or refresh-token storage").

    One row per signed-in browser. The refresh token is random and opaque; only
    its SHA-256 hash is stored. Exactly one of user_id / account_id is set.
    """

    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint("num_nonnulls(user_id, account_id) = 1", name="one_principal"),
        Index(
            "ix_auth_sessions_live_user",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index(
            "ix_auth_sessions_live_account",
            "account_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("ix_auth_sessions_previous_token_hash", "previous_token_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("complainant_accounts.id"))
    refresh_token_hash: Mapped[str] = mapped_column(Text, unique=True)
    previous_token_hash: Mapped[str | None] = mapped_column(Text)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
