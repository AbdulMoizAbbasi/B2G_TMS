from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class Tender(Base):
    __tablename__ = "tenders"

    jazzid: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("tender_sources.id"),
        nullable=False,
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

    estimated_value: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    estimated_value_source: Mapped[str | None] = mapped_column(
        String(100),
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

    source_detail_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    primary_document_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    raw_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    source = relationship(
        "TenderSource",
        back_populates="tenders",
    )

    relevance = relationship(
        "TenderRelevance",
        back_populates="tender",
        uselist=False,
        passive_deletes=True,
    )

    documents = relationship(
        "TenderDocument",
        back_populates="tender",
        passive_deletes=True,
    )

    participation = relationship(
        "TenderParticipation",
        back_populates="tender",
        uselist=False,
        passive_deletes=True,
    )

    field_override = relationship(
        "TenderFieldOverride",
        back_populates="tender",
        uselist=False,
        passive_deletes=True,
    )