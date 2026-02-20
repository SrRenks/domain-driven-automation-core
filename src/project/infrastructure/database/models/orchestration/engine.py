from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from . import OrchestrationInstanceModel

from sqlalchemy import String, Index, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...base import Base
from ...mixins import TimestampMixin, AuditMixin, VersionMixin


class EngineModel(Base, TimestampMixin, AuditMixin, VersionMixin):
    """Engine database model.

    Represents an external orchestration system (e.g., Jenkins, Argo).

    Attributes:
        name (Mapped[str]): Unique name of the engine.
        type (Mapped[str]): Engine type classification.
        is_active (Mapped[bool]): Soft delete flag.
        instances (Mapped[List["OrchestrationInstanceModel"]]): Instances created in this engine.
    """
    __tablename__ = "engine"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    instances: Mapped[List["OrchestrationInstanceModel"]] = relationship(
        back_populates="engine",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_engine_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the engine model.

        Returns:
            str: Representation including name and type.
        """
        return f"<EngineModel: {self.name} ({self.type})>"
