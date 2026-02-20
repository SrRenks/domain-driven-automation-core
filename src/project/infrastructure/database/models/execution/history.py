from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .item_execution import ItemExecutionModel

from sqlalchemy import DateTime, ForeignKey, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLAlchemyEnum

from ...base import Base
from .....domain.enums import ExecutionStatus

class ItemStateHistoryModel(Base):
    """Item State History database model.

    Immutable audit trail of status changes for item executions.

    Attributes:
        id (Mapped[UUID]): Primary key (generated automatically).
        item_execution_id (Mapped[UUID]): Foreign key to the item execution.
        previous_status (Mapped[Optional[ExecutionStatus]]): Status before transition.
        new_status (Mapped[ExecutionStatus]): Status after transition.
        changed_at (Mapped[datetime]): When the transition occurred.
        created_at (Mapped[datetime]): When the record was created.
        created_by (Mapped[Optional[str]]): User who triggered the transition.
        item_execution (Mapped["ItemExecutionModel"]): Related item execution.
    """
    __tablename__ = "item_state_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    item_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("item_execution.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[ExecutionStatus]] = mapped_column(
        SQLAlchemyEnum(ExecutionStatus, name="executionstatus", create_type=False)
    )
    new_status: Mapped[ExecutionStatus] = mapped_column(
        SQLAlchemyEnum(ExecutionStatus, name="executionstatus", create_type=False),
        nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )

    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    item_execution: Mapped["ItemExecutionModel"] = relationship(back_populates="state_history")

    __table_args__ = (
        Index("ix_state_history_item_changed", "item_execution_id", "changed_at"),
    )