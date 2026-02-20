from uuid import uuid4

import pytest

from src.project.domain.entities.definition import Automation, Batch, Item
from src.project.domain.exceptions import ValidationError


class TestAutomation:
    """Test suite for the Automation domain entity."""
    def test_create_automation(self):
        """Test basic creation of an Automation with name and description.

        Verifies that name, description, is_active, and version are set correctly.
        """
        auto = Automation(name="test", description="desc")
        assert auto.name == "test"
        assert auto.description == "desc"
        assert auto.is_active is True
        assert auto.version == 1

    def test_deactivate_active_automation(self):
        """Test deactivating an active automation.

        Expect is_active to become False.
        """
        auto = Automation(name="test")
        auto.deactivate()
        assert auto.is_active is False

    def test_activate_inactive_automation(self):
        """Test activating an inactive automation.

        Expect is_active to become True.
        """
        auto = Automation(name="test")
        auto.deactivate()
        auto.activate()
        assert auto.is_active is True

    def test_update_schemas_valid(self):
        """Test updating batch and item schemas with valid JSON schemas.

        Verifies that the schemas are stored correctly.
        """
        auto = Automation(name="test")
        schema = {"type": "object", "properties": {}}
        auto.update_schemas(batch_schema=schema, item_schema=schema)
        assert auto.batch_schema == schema
        assert auto.item_schema == schema

    def test_update_schemas_invalid_batch_schema_raises(self):
        """Test that updating with an invalid batch schema raises ValidationError."""
        auto = Automation(name="test")
        with pytest.raises(ValidationError, match="Invalid JSON Schema"):
            auto.update_schemas(batch_schema={"type": "invalid"})

    def test_update_schemas_invalid_item_schema_raises(self):
        """Test that updating with an invalid item schema raises ValidationError."""
        auto = Automation(name="test")
        with pytest.raises(ValidationError, match="Invalid JSON Schema"):
            auto.update_schemas(item_schema={"type": "invalid"})

    def test_validate_batch_payload_with_schema(self):
        """Test batch payload validation against a defined schema.

        Should return valid True for correct payload, False for incorrect.
        """
        auto = Automation(
            name="test",
            batch_schema={"type": "object", "properties": {"a": {"type": "string"}}},
        )
        result = auto.validate_batch_payload({"a": "hello"})
        assert result.valid is True
        result = auto.validate_batch_payload({"a": 123})
        assert result.valid is False

    def test_validate_item_payload_with_schema(self):
        """Test item payload validation against a defined schema."""
        auto = Automation(name="test", item_schema={"type": "integer"})
        result = auto.validate_item_payload(5)
        assert result.valid is True
        result = auto.validate_item_payload("x")
        assert result.valid is False

    def test_validate_payload_without_schema(self):
        """Test payload validation when no schema is defined.

        Should always return valid True with empty errors.
        """
        auto = Automation(name="test")
        result = auto.validate_batch_payload({"any": "data"})
        assert result.valid is True
        assert result.errors == []

    def test_automation_name_empty_raises(self):
        """Test that creating an automation with empty/whitespace name raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            Automation(name="   ")

    def test_automation_invalid_batch_schema_raises(self):
        """Test that providing an invalid batch schema during creation raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid JSON Schema"):
            Automation(name="test", batch_schema={"type": "invalid"})

    def test_automation_invalid_item_schema_raises(self):
        """Test that providing an invalid item schema during creation raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid JSON Schema"):
            Automation(name="test", item_schema={"type": "invalid"})

    def test_repr(self):
        """Test that the __repr__ method returns a string containing class name, name, and ID."""
        auto = Automation(name="test")
        auto.id = uuid4()
        repr_str = repr(auto)
        assert "Automation" in repr_str
        assert auto.name in repr_str
        assert str(auto.id) in repr_str


class TestBatch:
    """Test suite for the Batch domain entity."""
    def test_create_batch(self):
        """Test basic creation of a Batch with automation_id, name, and payload."""
        automation_id = uuid4()
        batch = Batch(automation_id=automation_id, name="batch1", payload={"key": "value"})
        assert batch.automation_id == automation_id
        assert batch.name == "batch1"
        assert batch.payload == {"key": "value"}
        assert batch.is_active is True

    def test_deactivate_batch(self):
        """Test deactivating a batch (soft delete)."""
        batch = Batch(automation_id=uuid4(), name="test")
        batch.deactivate()
        assert batch.is_active is False

    def test_activate_batch(self):
        """Test reactivating a deactivated batch."""
        batch = Batch(automation_id=uuid4(), name="test")
        batch.deactivate()
        batch.activate()
        assert batch.is_active is True


class TestItem:
    """Test suite for the Item domain entity."""
    def test_create_item(self):
        """Test basic creation of an Item with batch_id, sequence_number, and payload."""
        batch_id = uuid4()
        item = Item(batch_id=batch_id, sequence_number=1, payload={"data": "x"})
        assert item.batch_id == batch_id
        assert item.sequence_number == 1
        assert item.payload == {"data": "x"}
        assert item.is_active is True

    def test_deactivate_item(self):
        """Test deactivating an item."""
        item = Item(batch_id=uuid4(), sequence_number=1)
        item.deactivate()
        assert item.is_active is False

    def test_activate_item(self):
        """Test reactivating a deactivated item."""
        item = Item(batch_id=uuid4(), sequence_number=1)
        item.deactivate()
        item.activate()
        assert item.is_active is True