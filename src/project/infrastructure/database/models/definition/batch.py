from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .automation import AutomationModel
    from .item import ItemModel
    from ..execution.batch_execution import BatchExecutionModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, UniqueConstraint, Index, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB

from ...base import Base
from ...mixins import TimestampMixin, AuditMixin, VersionMixin


class BatchModel(Base, TimestampMixin, AuditMixin, VersionMixin):
    """Batch database model.

    Represents a logical group of items within an automation.

    Attributes:
        automation_id (Mapped[UUID]): Foreign key to parent automation.
        name (Mapped[str]): Name of the batch (unique per automation).
        payload (Mapped[Optional[dict]]): JSON payload for batch-level configuration.
        is_active (Mapped[bool]): Soft delete flag.
        automation (Mapped["AutomationModel"]): Parent automation relationship.
        items (Mapped[List["ItemModel"]]): Items in this batch, ordered by sequence_number.
        executions (Mapped[List["BatchExecutionModel"]]): Executions of this batch.
    """
    __tablename__ = "batch"

    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    automation: Mapped["AutomationModel"] = relationship(back_populates="batches")

    items: Mapped[List["ItemModel"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="ItemModel.sequence_number",
    )

    executions: Mapped[List["BatchExecutionModel"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("automation_id", "name", name="uq_batch_automation_name"),
        Index("ix_batch_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the batch model.

        Returns:
            str: Representation including id and name.
        """
        return f"<BatchModel id={self.id} name={self.name}>"
