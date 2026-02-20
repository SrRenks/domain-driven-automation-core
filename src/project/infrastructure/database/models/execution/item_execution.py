from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..execution.run import RunModel
    from ..execution.batch_execution import BatchExecutionModel
    from .history import ItemStateHistoryModel
    from ..definition.item import ItemModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Index, String, Boolean, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from ...mixins import TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin, RetryableMixin
from ...base import Base


class ItemExecutionModel(Base, TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin, RetryableMixin):
    """Item Execution database model.

    Tracks the execution of individual items with retry support.

    Attributes:
        run_id (Mapped[UUID]): Foreign key to parent run.
        batch_execution_id (Mapped[UUID]): Foreign key to parent batch execution.
        item_id (Mapped[UUID]): Foreign key to the item being executed.
        result_payload (Mapped[Optional[dict]]): Output from successful execution.
        error_message (Mapped[Optional[str]]): Error details if failed.
        is_active (Mapped[bool]): Soft delete flag.
        run (Mapped["RunModel"]): Parent run relationship.
        batch_execution (Mapped["BatchExecutionModel"]): Parent batch execution relationship.
        item (Mapped["ItemModel"]): Related item.
        state_history (Mapped[List["ItemStateHistoryModel"]]): History of status changes.
    """
    __tablename__ = "item_execution"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("run.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("batch_execution.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("item.id", ondelete="CASCADE"),
        nullable=False,
    )

    result_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    run: Mapped["RunModel"] = relationship(back_populates="item_executions")
    batch_execution: Mapped["BatchExecutionModel"] = relationship(back_populates="item_executions")
    item: Mapped["ItemModel"] = relationship(back_populates="executions")

    state_history: Mapped[List["ItemStateHistoryModel"]] = relationship(
        back_populates="item_execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_item_execution_run_id", "run_id"),
        Index("ix_item_execution_batch_execution_id", "batch_execution_id"),
        Index("ix_item_execution_item_id", "item_id"),
        Index("ix_item_execution_is_active", "is_active"),
        UniqueConstraint("run_id", "item_id", name="uq_item_execution_run_item"),
    )
