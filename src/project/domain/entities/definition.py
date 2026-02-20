from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID

from jsonschema import SchemaError, Draft7Validator

from ..base import DomainEntity
from ..exceptions.domain import ValidationError

from ..value_objects.schemas import Schema, SchemaValidationResult



@dataclass
class Automation(DomainEntity):
    """Core configuration entity representing an automated process definition.

    Serves as the root aggregate for all automation-related entities; defines the
    blueprint for batches and items.

    Attributes:
        name (str): Unique identifier (required, stripped).
        description (Optional[str]): Optional explanation.
        batch_schema (Optional[Dict[str, Any]]): JSON schema for batch payloads.
        item_schema (Optional[Dict[str, Any]]): JSON schema for item payloads.
    """
    name: str
    description: Optional[str] = None
    batch_schema: Optional[Dict[str, Any]] = None
    item_schema: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate automation name and schemas after initialization.

        Raises:
            ValidationError: If name is empty or schemas are invalid JSON Schema.
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Automation", "name", "cannot be empty")
        self.name = self.name.strip()

        if self.batch_schema is not None:
            try:
                Draft7Validator.check_schema(self.batch_schema)
            except SchemaError as e:
                raise ValidationError(
                    "Automation", "batch_schema",
                    f"Invalid JSON Schema: {e.message}"
                ) from e

        if self.item_schema is not None:
            try:
                Draft7Validator.check_schema(self.item_schema)
            except SchemaError as e:
                raise ValidationError(
                    "Automation", "item_schema",
                    f"Invalid JSON Schema: {e.message}"
                ) from e

    def update_schemas(
        self,
        batch_schema: Optional[Dict[str, Any]] = None,
        item_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update batch and item schemas after validating them.

        Args:
            batch_schema (Optional[Dict[str, Any]]): New batch schema.
            item_schema (Optional[Dict[str, Any]]): New item schema.

        Raises:
            ValidationError: If any provided schema is invalid JSON Schema.
        """
        if batch_schema is not None:
            try:
                Draft7Validator.check_schema(batch_schema)
            except SchemaError as e:
                raise ValidationError(
                    "Automation", "batch_schema",
                    f"Invalid JSON Schema: {e.message}"
                ) from e
            self.batch_schema = batch_schema

        if item_schema is not None:
            try:
                Draft7Validator.check_schema(item_schema)
            except SchemaError as e:
                raise ValidationError(
                    "Automation", "item_schema",
                    f"Invalid JSON Schema: {e.message}"
                ) from e
            self.item_schema = item_schema

    def validate_batch_payload(self, payload: Dict[str, Any]) -> SchemaValidationResult:
        """Validate a batch payload against the batch schema, if present.

        Args:
            payload (Dict[str, Any]): The payload to validate.

        Returns:
            SchemaValidationResult: Validation result (valid=True if no schema).
        """
        if self.batch_schema:
            return Schema(self.batch_schema).validate(payload)
        return SchemaValidationResult(valid=True, errors=[])

    def validate_item_payload(self, payload: Dict[str, Any]) -> SchemaValidationResult:
        """Validate an item payload against the item schema, if present.

        Args:
            payload (Dict[str, Any]): The payload to validate.

        Returns:
            SchemaValidationResult: Validation result (valid=True if no schema).
        """
        if self.item_schema:
            return Schema(self.item_schema).validate(payload)
        return SchemaValidationResult(valid=True, errors=[])

@dataclass
class Batch(DomainEntity):
    """Batch domain entity - groups items within an automation.

    Attributes:
        automation_id (UUID): Reference to parent Automation.
        name (str): Unique name within automation (stripped).
        payload (Optional[Dict[str, Any]]): Batch-level configuration.
    """

    automation_id: UUID
    name: str
    payload: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If name is empty or automation_id is missing.
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Batch", "name", "cannot be empty")
        if not self.automation_id:
            raise ValidationError("Batch", "automation_id", "is required")
        self.name = self.name.strip()

    def update_payload(self, payload: Dict[str, Any]) -> None:
        """Update the batch payload.

        Args:
            payload (Dict[str, Any]): New payload.
        """
        self.payload = payload


@dataclass
class Item(DomainEntity):
    """Item domain entity - atomic unit of work within a batch.

    Attributes:
        batch_id (UUID): Reference to parent Batch.
        sequence_number (int): Position within batch (>=0).
        payload (Optional[Dict[str, Any]]): Item-specific content.
    """
    batch_id: UUID
    sequence_number: int
    payload: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If sequence_number < 0 or batch_id missing.
        """
        if self.sequence_number < 0:
            raise ValidationError("Item", "sequence_number", "must be >= 0")
        if not self.batch_id:
            raise ValidationError("Item", "batch_id", "is required")

    def update_payload(self, payload: Dict[str, Any]) -> None:
        """Update the item payload.

        Args:
            payload (Dict[str, Any]): New payload.
        """
        self.payload = payload
