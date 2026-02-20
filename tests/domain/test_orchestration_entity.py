from uuid import uuid4

import pytest

from src.project.domain.entities.orchestration import Engine, OrchestrationInstance
from src.project.domain.enums import ExecutionStatus
from src.project.domain.exceptions import InvalidStateError, ValidationError


class TestEngine:
    """Test suite for Engine entity."""
    def test_create_engine(self):
        """Test engine creation with name and type."""
        engine = Engine(name="test-engine", type="docker")
        assert engine.name == "test-engine"
        assert engine.type == "docker"
        assert engine.is_active is True

    def test_deactivate_engine(self):
        """Test deactivating an engine."""
        engine = Engine(name="test", type="docker")
        engine.deactivate()
        assert engine.is_active is False

    def test_activate_engine(self):
        """Test activating a deactivated engine."""
        engine = Engine(name="test", type="docker")
        engine.deactivate()
        engine.activate()
        assert engine.is_active is True


class TestOrchestrationInstance:
    """Test suite for OrchestrationInstance entity."""
    def test_create_instance(self):
        """Test instance creation with engine_id, external_id, status, metadata, and duration."""
        engine_id = uuid4()
        instance = OrchestrationInstance(
            engine_id=engine_id,
            external_id="ext-123",
            status=ExecutionStatus.PENDING,
            instance_metadata={"key": "value"},
            duration_seconds=None,
        )
        assert instance.engine_id == engine_id
        assert instance.external_id == "ext-123"
        assert instance.status == ExecutionStatus.PENDING
        assert instance.instance_metadata == {"key": "value"}
        assert instance.duration_seconds is None

    def test_start_instance(self):
        """Test starting an instance."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext", status=ExecutionStatus.PENDING)
        instance.start()
        assert instance.status == ExecutionStatus.PROCESSING
        assert instance.started_at is not None

    def test_start_already_started_raises(self):
        """Test starting an already started instance raises InvalidStateError."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext", status=ExecutionStatus.PROCESSING)
        with pytest.raises(InvalidStateError):
            instance.start()

    def test_complete_instance(self):
        """Test completing an instance."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext")
        instance.start()
        instance.complete()
        assert instance.status == ExecutionStatus.COMPLETED
        assert instance.finished_at is not None

    def test_fail_instance(self):
        """Test failing an instance."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext")
        instance.start()
        instance.fail()
        assert instance.status == ExecutionStatus.FAILED
        assert instance.finished_at is not None

    def test_complete_instance_not_started_raises(self):
        """Test completing an instance that hasn't started raises InvalidStateError."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext")
        with pytest.raises(InvalidStateError):
            instance.complete()

    def test_fail_already_finished_raises(self):
        """Test failing an already finished instance raises InvalidStateError."""
        instance = OrchestrationInstance(engine_id=uuid4(), external_id="ext")
        instance.start()
        instance.complete()
        with pytest.raises(InvalidStateError):
            instance.fail()

    def test_orchestration_instance_missing_engine_id_raises(self):
        """Test that missing engine_id raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestrationInstance(engine_id=None, external_id="ext", status=ExecutionStatus.PENDING)

    def test_orchestration_instance_missing_external_id_raises(self):
        """Test that missing external_id raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestrationInstance(engine_id=uuid4(), external_id=None, status=ExecutionStatus.PENDING)
