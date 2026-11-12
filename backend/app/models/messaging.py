"""Messages to complainants (DB doc 4.2 and 4.3). OTP messages for sign-up use the same tables."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import MessageChannel, MessageState, MessageType
from app.db.base import Base
from app.db.types import MessageChannelType, MessageStateType, MessageTypeType


class MessageTemplate(Base):
    """DB doc 4.2: the text of MSG-1, MSG-2, MSG-3 and the OTP message, per channel. Edited by Admin."""

    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint("message_type", "channel", name="uq_message_templates_type_channel"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    message_type: Mapped[MessageType] = mapped_column(MessageTypeType)
    channel: Mapped[MessageChannel] = mapped_column(MessageChannelType)
    subject: Mapped[str | None] = mapped_column(Text)  # email only
    body: Mapped[str] = mapped_column(Text)  # placeholders such as {reference_number} and {solution_text}
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # the admin who last edited it
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OutboundMessage(Base):
    """DB doc 4.3: a log of every message the workflow sends.

    Messages are sent directly by the workflow, so this table records the
    result and is never a queue. A failed row never blocks anything.
    """

    __tablename__ = "outbound_messages"
    __table_args__ = (
        CheckConstraint("message_type = 'otp' OR complaint_id IS NOT NULL", name="case_message_has_complaint"),
        # A case never gets the same message twice.
        Index(
            "uq_outbound_messages_one_sent_per_case",
            "complaint_id",
            "message_type",
            unique=True,
            postgresql_where=text("state = 'sent' AND message_type <> 'otp'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))  # null for OTP messages
    complainant_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("complainant_accounts.id", name="fk_outbound_messages_complainant_account_id_accounts")
    )  # set for OTP messages
    message_type: Mapped[MessageType] = mapped_column(MessageTypeType)
    channel: Mapped[MessageChannel] = mapped_column(MessageChannelType)
    recipient: Mapped[str] = mapped_column(Text)  # phone number or email address
    body: Mapped[str] = mapped_column(Text)  # the text sent; for OTP, stored with the code masked
    state: Mapped[MessageState] = mapped_column(MessageStateType)
    error_detail: Mapped[str | None] = mapped_column(Text)  # gateway error for failed messages
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
