from uuid import uuid4

import pytest

from src.project.domain.entities import Automation, Run, ItemExecution
from src.project.domain.enums import ExecutionStatus
from src.project.domain.exceptions import ValidationError, InvalidStateError


class TestAutomation:
    """Test suite for the Automation entity (additional tests)."""
    def test_automation_creation(self):
        """Test automation creation with name and description."""
        auto = Automation(name="test", description="desc")
        assert auto.name == "test"
        assert auto.description == "desc"
        assert auto.is_active is True

    def test_automation_name_stripped(self):
        """Test that leading/trailing whitespace is stripped from name."""
        auto = Automation(name="  test  ")
        assert auto.name == "test"

    def test_automation_empty_name_raises(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            Automation(name="")

    def test_automation_update_schemas_valid(self):
        """Test updating schemas with valid JSON."""
        auto = Automation(name="test")
        schema = {"type": "object"}
        auto.update_schemas(batch_schema=schema)
        assert auto.batch_schema == schema

    def test_automation_update_schemas_invalid_raises(self):
        """Test that invalid schema update raises ValidationError."""
        auto = Automation(name="test")
        invalid_schema = {"type": "invalid_type"}
        with pytest.raises(ValidationError, match="Invalid JSON Schema"):
            auto.update_schemas(batch_schema=invalid_schema)


class TestRun:
    """Test suite for the Run entity."""
    def test_run_start(self):
        """Test starting a run transitions to PROCESSING and increments version."""
        run = Run(automation_id=uuid4())
        run.start()
        assert run.status == ExecutionStatus.PROCESSING
        assert run.started_at is not None
        assert run.version == 2

    def test_run_start_invalid_state(self):
        """Test that starting an already started run raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        run.start()
        with pytest.raises(InvalidStateError):
            run.start()

    def test_run_complete(self):
        """Test completing a run transitions to COMPLETED and sets finished_at."""
        run = Run(automation_id=uuid4())
        run.start()
        run.complete()
        assert run.status == ExecutionStatus.COMPLETED
        assert run.finished_at is not None
        assert run.version == 3

    def test_run_complete_without_start_raises(self):
        """Test that completing a run that hasn't started raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        with pytest.raises(InvalidStateError):
            run.complete()

    def test_run_fail(self):
        """Test failing a run sets status to FAILED and records error summary."""
        run = Run(automation_id=uuid4())
        run.start()
        run.fail("error")
        assert run.status == ExecutionStatus.FAILED
        assert run.error_summary == "error"
        assert run.finished_at is not None

    def test_run_cancel(self):
        """Test cancelling a run sets status to CANCELLED and records reason."""
        run = Run(automation_id=uuid4())
        run.start()
        run.cancel("user request")
        assert run.status == ExecutionStatus.CANCELLED
        assert run.cancellation_reason == "user request"


class TestItemExecution:
    """Test suite for the ItemExecution entity."""
    def test_item_execution_start(self):
        """Test starting an item execution increments attempt count and sets status PROCESSING."""
        item_exec = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=3,
        )
        item_exec.start()
        assert item_exec.status == ExecutionStatus.PROCESSING
        assert item_exec.attempt_count == 1
        assert item_exec.started_at is not None

    def test_item_execution_start_exceeds_max_attempts(self):
        """Test that starting beyond max_attempts raises InvalidStateError."""
        item_exec = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=1,
        )
        item_exec.start()
        with pytest.raises(InvalidStateError, match="max attempts 1 already reached"):
            item_exec.start()

    def test_item_execution_fail_with_retry(self):
        """Test that fail when retries remain sets status to RETRYING and does not finish."""
        item_exec = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=3,
        )
        item_exec.start()
        item_exec.fail("timeout")
        assert item_exec.status == ExecutionStatus.RETRYING
        assert item_exec.error_message == "timeout"
        assert item_exec.finished_at is None

    def test_item_execution_fail_no_retry(self):
        """Test that fail when no retries remain sets status to FAILED and finishes."""
        item_exec = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=1,
        )
        item_exec.start()
        item_exec.fail("fatal")
        assert item_exec.status == ExecutionStatus.FAILED
        assert item_exec.finished_at is not None

    def test_can_retry(self):
        """Test the can_retry method under various attempt counts and max_attempts."""
        item_exec = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=3,
        )
        assert item_exec.can_retry() is True
        item_exec.start()
        assert item_exec.can_retry() is True
        item_exec.fail("error")
        assert item_exec.can_retry() is True
        item_exec.start()
        item_exec.fail("error again")
        item_exec.start()
        item_exec.fail("error again")
        assert item_exec.can_retry() is False
