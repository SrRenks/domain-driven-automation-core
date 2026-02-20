from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from . import BatchModel
    from ..execution.run import RunModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, String, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB

from ...mixins import TimestampMixin, AuditMixin, VersionMixin
from ...base import Base

class AutomationModel(Base, TimestampMixin, AuditMixin, VersionMixin):
    """Automation ORM model.

    Represents an automation definition in the database.

    Attributes:
        name (Mapped[str]): Unique identifier for the automation.
        description (Mapped[Optional[str]]): Optional description.
        is_active (Mapped[bool]): Soft delete flag (True = active).
        batch_schema (Mapped[Optional[dict]]): JSON schema for batch payloads.
        item_schema (Mapped[Optional[dict]]): JSON schema for item payloads.
        batches (Mapped[List["BatchModel"]]): Related batches (one-to-many).
        runs (Mapped[List["RunModel"]]): Related runs (one-to-many).
    """
    __tablename__ = "automation"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    batch_schema: Mapped[Optional[dict]] = mapped_column(JSONB)
    item_schema: Mapped[Optional[dict]] = mapped_column(JSONB)

    batches: Mapped[List["BatchModel"]] = relationship(
        back_populates="automation",
        cascade="all, delete-orphan",
    )

    runs: Mapped[List["RunModel"]] = relationship(
        back_populates="automation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_automation_name", "name"),
        Index("ix_automation_is_active", "is_active"),
        Index("ix_automation_name_active", "name",
              postgresql_where=text("is_active = true"),
              unique=True),
    )

    def __repr__(self) -> str:
        """Return a string representation of the automation model.

        Returns:
            str: Representation including id and name.
        """
        return f"<AutomationModel id={self.id} name={self.name}>"
