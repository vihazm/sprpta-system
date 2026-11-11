from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthCheck(Base):
    """One reading of one service, taken about once a minute (see health_check_service).

    `status` is "ok", "slow" or "down". `latency_ms` is empty when the service did not answer.
    """

    __tablename__ = "health_checks"
    __table_args__ = (Index("ix_health_checks_service_checked_at", "service", "checked_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    service: Mapped[str] = mapped_column(Text)  # "web", "api" or "database"
    status: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
