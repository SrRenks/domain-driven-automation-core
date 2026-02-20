from dataclasses import dataclass
from typing import Dict, Any, List
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from ..exceptions.domain import ValidationError


@dataclass(frozen=True)
class Schema:
    """Immutable JSON schema value object for batch and item validation.

    Attributes:
        definition (Dict[str, Any]): The JSON schema definition.
    """
    definition: Dict[str, Any]

    def __post_init__(self):
        """Validate that the schema definition is a dictionary.

        Raises:
            ValidationError: If `definition` is not a dict.
        """
        if not isinstance(self.definition, dict):
            raise ValidationError("Schema", "definition", "must be a dictionary")

    def validate(self, data: Dict[str, Any]) -> 'SchemaValidationResult':
        """Validate input data against the schema.

        Args:
            data (Dict[str, Any]): The data to validate.

        Returns:
            SchemaValidationResult: Result containing validity status and error list.
        """
        try:
            validate(instance=data, schema=self.definition)
            return SchemaValidationResult(valid=True, errors=[])
        except JsonSchemaValidationError as e:
            return SchemaValidationResult(valid=False, errors=[str(e)])


@dataclass(frozen=True)
class SchemaValidationResult:
    """Immutable result of schema validation.

    Attributes:
        valid (bool): True if validation succeeded.
        errors (List[str]): List of error messages (empty if valid).
    """
    valid: bool
    errors: List[str]
