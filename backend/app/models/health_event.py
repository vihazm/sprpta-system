from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthEvent(Base):
    """Something worth telling the administrator: a service changed state, or one started.

    `status` is the state it changed to: "ok" (back to normal), "slow", "down" or "started".
    """

    __tablename__ = "health_events"
    __table_args__ = (Index("ix_health_events_occurred_at", "occurred_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    service: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
