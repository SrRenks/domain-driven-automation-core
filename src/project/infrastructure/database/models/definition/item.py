from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .batch import BatchModel
    from ..execution.item_execution import ItemExecutionModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Integer, UniqueConstraint, Index, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB

from ...base import Base
from ...mixins import TimestampMixin, AuditMixin, VersionMixin


class ItemModel(Base, TimestampMixin, AuditMixin, VersionMixin):
    """Item database model.

    Represents an atomic unit of work within a batch.

    Attributes:
        batch_id (Mapped[UUID]): Foreign key to parent batch.
        sequence_number (Mapped[int]): Position within the batch (>=0).
        payload (Mapped[Optional[dict]]): JSON payload for item-specific content.
        is_active (Mapped[bool]): Soft delete flag.
        batch (Mapped["BatchModel"]): Parent batch relationship.
        executions (Mapped[List["ItemExecutionModel"]]): Executions of this item.
    """
    __tablename__ = "item"

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    batch: Mapped["BatchModel"] = relationship(back_populates="items")

    executions: Mapped[List["ItemExecutionModel"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "sequence_number", name="uq_item_batch_sequence"),
        Index("ix_item_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the item model.

        Returns:
            str: Representation including id and sequence number.
        """
        return f"<ItemModel id={self.id} seq={self.sequence_number}>"