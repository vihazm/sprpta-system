from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import MessageChannel
from app.db.base import Base
from app.db.types import MessageChannelType


class OtpCode(Base):
    """DB doc 2.3: one-time passwords for portal sign-up.

    Only a hash of the code is stored. `attempts` counts wrong guesses and
    `consumed_at` is set once the code has been used.
    """

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complainant_account_id: Mapped[int] = mapped_column(ForeignKey("complainant_accounts.id"))
    channel: Mapped[MessageChannel] = mapped_column(MessageChannelType)  # sms for phone, email for email
    code_hash: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
