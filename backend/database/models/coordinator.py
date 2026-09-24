from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class Coordinator(Base):
    __tablename__ = "coordinators"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="coordinator",
    )

    region = relationship(
        "Region",
        back_populates="coordinator",
    )