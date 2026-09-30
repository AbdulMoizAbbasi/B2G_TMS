from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    employees = relationship(
        "Employee",
        back_populates="region",
    )

    coordinator = relationship(
        "Coordinator",
        back_populates="region",
        uselist=False,
    )

    tenders = relationship(
        "Tender",
        back_populates="region",
    )

    tender_region_assignments = relationship(
        "TenderRegionAssignment",
        back_populates="region",
    )