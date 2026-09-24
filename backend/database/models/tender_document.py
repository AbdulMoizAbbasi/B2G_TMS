from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    tender_jazzid: Mapped[int] = mapped_column(
        ForeignKey("tenders.jazzid"),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    document_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    local_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    download_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    downloaded_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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
        back_populates="documents",
    )