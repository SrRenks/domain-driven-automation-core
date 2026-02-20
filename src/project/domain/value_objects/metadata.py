from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..base import ValueObject


@dataclass(frozen=True)
class AuditInfo(ValueObject):
    """Immutable audit information value object.

    Encapsulates audit metadata for entities that track creation and modification.

    Attributes:
        created_at (Optional[datetime]): Timestamp of creation.
        created_by (Optional[str]): User who created the entity.
        updated_at (Optional[datetime]): Timestamp of last update.
        updated_by (Optional[str]): User who last updated the entity.
    """
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


@dataclass(frozen=True)
class VersionInfo(ValueObject):
    """Immutable version information value object.

    Represents a version number and provides an increment operation.

    Attributes:
        version (int): Version number. Defaults to 1.
    """
    version: int = 1

    def increment(self) -> 'VersionInfo':
        """Create a new VersionInfo with version incremented by 1.

        Returns:
            VersionInfo: A new instance with version = current version + 1.
        """
        return VersionInfo(version=self.version + 1)
