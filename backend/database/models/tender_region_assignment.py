from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class TenderRegionAssignment(Base):
    __tablename__ = "tender_region_assignments"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    tender_jazzid: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tenders.jazzid",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "regions.id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    assignment_type: Mapped[str] = mapped_column(
        Enum("AUTO", "ADMIN"),
        nullable=False,
    )

    assigned_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    tender = relationship(
        "Tender",
        back_populates="region_assignments",
    )

    region = relationship(
        "Region",
        back_populates="tender_region_assignments",
    )