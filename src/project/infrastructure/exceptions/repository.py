from typing import Optional
from uuid import UUID


class RepositoryError(Exception):
    """Base exception for repository errors.

    Attributes:
        message (str): Error description.
        original_error (Optional[Exception]): Original exception that caused this error.
    """
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found in the database.

    Attributes:
        entity_name (str): Name of the entity type.
        entity_id (UUID): The ID that was not found.
    """
    def __init__(self, entity_name: str, entity_id: UUID):
        self.entity_name = entity_name
        self.entity_id = entity_id
        message = f"{entity_name} with id {entity_id} not found"
        super().__init__(message)


class DuplicateEntityError(RepositoryError):
    """Raised when attempting to create an entity that violates a unique constraint.

    Attributes:
        entity_name (str): Name of the entity type.
        constraint_info (str): Description of the violated constraint.
    """
    def __init__(self, entity_name: str, constraint_info: str):
        self.entity_name = entity_name
        self.constraint_info = constraint_info
        message = f"Duplicate {entity_name}: {constraint_info}"
        super().__init__(message)


class ConcurrencyError(RepositoryError):
    """Raised when optimistic locking version mismatch occurs.

    Attributes:
        entity_name (str): Name of the entity type.
        entity_id (UUID): ID of the entity.
        expected_version (int): Version the caller expected.
        actual_version (int): Current version in the database.
        extra (Optional[str]): Additional context.
    """
    def __init__(self, entity_name: str, entity_id: UUID, expected_version: int, actual_version: int, extra: Optional[str] = None):
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        message = (
            f"Concurrency conflict on {entity_name} {entity_id}: "
            f"expected version {expected_version}, actual version {actual_version}"
        )
        self.extra = extra
        super().__init__(message)
