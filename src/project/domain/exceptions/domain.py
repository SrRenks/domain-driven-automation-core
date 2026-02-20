from typing import Optional
from uuid import UUID


class DomainError(Exception):
    """Base exception for all domain errors.

    Attributes:
        message (str): Error description.
        original_error (Optional[Exception]): Original exception that caused this error.
    """
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class ValidationError(DomainError):
    """Raised when domain validation fails (e.g., invalid field value).

    Attributes:
        entity_name (str): Name of the entity or value object.
        field (str): Specific field that failed validation.
        reason (str): Explanation of why validation failed.
    """
    def __init__(self, entity_name: str, field: str, reason: str):
        self.entity_name = entity_name
        self.field = field
        self.reason = reason
        message = f"Validation failed for {entity_name}.{field}: {reason}"
        super().__init__(message)


class InvalidStateError(DomainError):
    """Raised when an operation is attempted on an entity in an inappropriate state.

    Attributes:
        entity_name (str): Type of entity.
        entity_id (UUID): ID of the entity.
        current_state (str): Current state value (e.g., status).
        operation (str): Name of the operation attempted.
    """
    def __init__(self, entity_name: str, entity_id: UUID, current_state: str, operation: str):
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.current_state = current_state
        self.operation = operation
        message = f"Cannot {operation} {entity_name} {entity_id} in state {current_state}"
        super().__init__(message)
