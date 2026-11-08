from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Area(Base):
    """DB doc 2.4: Galle, Matara, Hambantota."""

    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
