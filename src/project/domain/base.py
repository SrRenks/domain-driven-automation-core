from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from .events import DomainEvent


@dataclass(frozen=True)
class ValueObject:
    """Base class for all immutable value objects.

    Value objects are compared by their attributes and must be hashable.
    This class enforces hashability of all fields in `__post_init__`.

    Attributes:
        (All attributes defined in subclasses must be hashable.)
    """

    def __post_init__(self):
        """Validate that all attributes are hashable.

        Raises:
            TypeError: If any attribute is not hashable.
        """
        for key, value in self.__dict__.items():
            try:
                hash(value)
            except TypeError:
                raise TypeError(
                    f"ValueObject attribute '{key}' must be hashable, "
                    f"got {type(value).__name__}"
                )

    def __eq__(self, other: object) -> bool:
        """Compare two value objects by their attributes.

        Args:
            other (object): Object to compare with.

        Returns:
            bool: True if other is of same class and has same attributes.
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """Compute hash based on sorted attribute items.

        Returns:
            int: Hash value of the value object.
        """
        return hash(tuple(sorted(self.__dict__.items())))

@dataclass
class DomainEntity:
    """Base class for all domain entities with soft delete support.

    Provides common fields: id, timestamps, audit, version, and soft delete flag.
    Also manages domain events.

    Attributes:
        id (UUID): Unique identifier (automatically generated).
        created_at (Optional[datetime]): Timestamp of creation.
        updated_at (Optional[datetime]): Timestamp of last update.
        created_by (Optional[str]): User who created the entity.
        updated_by (Optional[str]): User who last updated the entity.
        version (int): Optimistic locking version (starts at 1).
        is_active (bool): Soft delete flag (True = active).
        _events (List[DomainEvent]): List of domain events raised by this entity.
    """
    id: UUID = field(default_factory=uuid4, init=False)
    created_at: Optional[datetime] = field(default=None, init=False)
    updated_at: Optional[datetime] = field(default=None, init=False)
    created_by: Optional[str] = field(default=None, init=False)
    updated_by: Optional[str] = field(default=None, init=False)
    version: int = field(default=1, init=False)
    is_active: bool = field(default=True, init=False)
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __hash__(self) -> int:
        """Hash based on entity ID.

        Returns:
            int: Hash of the entity ID.
        """
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare two domain entities by class and ID.

        Args:
            other (object): Object to compare with.

        Returns:
            bool: True if other is same class and has same ID.
        """
        if not isinstance(other, DomainEntity):
            return False
        return self.id == other.id

    def register_event(self, event: DomainEvent) -> None:
        """Register a domain event to be dispatched later.

        Args:
            event (DomainEvent): The event to register.
        """
        self._events.append(event)

    def pop_events(self) -> List[DomainEvent]:
        """Retrieve and clear all registered events.

        Returns:
            List[DomainEvent]: List of events that have been registered.
        """
        events = self._events.copy()
        self._events.clear()
        return events

    def _bump_version(self) -> None:
        """Internal version increment for optimistic locking.

        Increments version and updates `updated_at` to current UTC time.
        """
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def touch(self, user: Optional[str] = None) -> None:
        """Update timestamps without changing version.

        Args:
            user (Optional[str], optional): User performing the touch.
                Defaults to None.
        """
        self.updated_at = datetime.now(timezone.utc)
        if user:
            self.updated_by = user

    def deactivate(self) -> None:
        """Soft delete the entity.

        Sets `is_active` to False and bumps the version.
        """
        self.is_active = False
        self._bump_version()

    def activate(self) -> None:
        """Reactivate a soft-deleted entity.

        Sets `is_active` to True and bumps the version.
        """
        self.is_active = True
        self._bump_version()
