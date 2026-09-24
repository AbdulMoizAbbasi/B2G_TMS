from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, JSON, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class TenderRelevance(Base):
    __tablename__ = "tender_relevance"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    tender_jazzid: Mapped[int] = mapped_column(
        ForeignKey("tenders.jazzid"),
        nullable=False,
        unique=True,
    )

    keyword_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        default=0,
    )

    matched_keywords: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    matched_capabilities: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    relevance_reason: Mapped[str | None] = mapped_column(
        Text,
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

    tender = relationship(
        "Tender",
        back_populates="relevance",
    )