from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class TenderParticipation(Base):
    __tablename__ = "tender_participation"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    tender_jazzid: Mapped[int] = mapped_column(
        ForeignKey("tenders.jazzid"),
        nullable=False,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NOT_REVIEWED",
    )

    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    delegated_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"),
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
        back_populates="participation",
    )

    decided_by_user = relationship(
        "User",
        back_populates="participation_decisions",
    )

    delegated_employee = relationship(
        "Employee",
        back_populates="delegated_tenders",
    )