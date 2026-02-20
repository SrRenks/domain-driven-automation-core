from datetime import datetime

import pytest

from src.project.domain.value_objects import Schema, AuditInfo, VersionInfo
from src.project.domain.exceptions import ValidationError


class TestSchema:
    """Test suite for Schema value object."""
    def test_schema_valid_definition(self):
        """Test creating a Schema with a valid dictionary."""
        schema = Schema(definition={"type": "object"})
        assert schema.definition == {"type": "object"}

    def test_schema_invalid_definition_raises(self):
        """Test that non-dict definition raises ValidationError."""
        with pytest.raises(ValidationError, match="must be a dictionary"):
            Schema(definition="not a dict")

    def test_schema_validate_valid_data(self):
        """Test validate returns valid True for data matching the schema."""
        schema = Schema(definition={"type": "object", "properties": {"name": {"type": "string"}}})
        result = schema.validate({"name": "John"})
        assert result.valid is True
        assert result.errors == []

    def test_schema_validate_invalid_data(self):
        """Test validate returns valid False with errors for invalid data."""
        schema = Schema(definition={"type": "object", "required": ["name"]})
        result = schema.validate({})
        assert result.valid is False
        assert len(result.errors) == 1


class TestAuditInfo:
    """Test suite for AuditInfo value object."""
    def test_audit_info_immutable(self):
        """Test that AuditInfo attributes cannot be changed (immutable)."""
        audit = AuditInfo(created_at=datetime.now(), created_by="admin")
        with pytest.raises(Exception):
            audit.created_by = "other"


class TestVersionInfo:
    """Test suite for VersionInfo value object."""
    def test_version_info_increment(self):
        """Test increment creates a new VersionInfo with version+1."""
        v1 = VersionInfo(version=1)
        v2 = v1.increment()
        assert v2.version == 2
        assert v1.version == 1
