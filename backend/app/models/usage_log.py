from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageLog(Base):
    """DB doc 5.2: usage logs (login, login_failed, logout, ...), viewed by Admin.

    Separate from the audit trail. For failed logins the typed identifier is
    deliberately not stored: it could be a password typed in the wrong field.
    """

    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("complainant_accounts.id"))
    event_type: Mapped[str] = mapped_column(Text)
    resource: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
