from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

class TenderFieldOverride(Base):
    __tablename__ = "tender_field_overrides"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    tender_jazzid: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenders.jazzid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    web_tender_no: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    tender_reference_no: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    tender_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authority: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    organization: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    estimated_value: Mapped[float | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    advertised_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    closed_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    overridden_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    overridden_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    tender = relationship(
        "Tender",
        back_populates="field_override",
    )

    user = relationship(
        "User",
        back_populates="tender_overrides",
    )