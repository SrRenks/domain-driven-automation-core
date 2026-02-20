from uuid import uuid4

import pytest

from src.project.domain.entities.execution import Run, BatchExecution, ItemExecution
from src.project.domain.enums import ExecutionStatus
from src.project.domain.exceptions import InvalidStateError, ValidationError


class TestRun:
    """Test suite for Run entity (comprehensive)."""
    def test_create_run(self):
        """Test run creation with automation_id and correlation_id."""
        automation_id = uuid4()
        run = Run(automation_id=automation_id, correlation_id="corr-1")
        assert run.automation_id == automation_id
        assert run.correlation_id == "corr-1"
        assert run.status == ExecutionStatus.PENDING
        assert run.started_at is None
        assert run.finished_at is None

    def test_start_run(self):
        """Test starting a run."""
        run = Run(automation_id=uuid4())
        run.start()
        assert run.status == ExecutionStatus.PROCESSING
        assert run.started_at is not None

    def test_start_already_started_raises(self):
        """Test starting a run that is already started raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        run.start()
        with pytest.raises(InvalidStateError):
            run.start()

    def test_complete_run(self):
        """Test completing a run."""
        run = Run(automation_id=uuid4())
        run.start()
        run.complete()
        assert run.status == ExecutionStatus.COMPLETED
        assert run.finished_at is not None

    def test_complete_without_start_raises(self):
        """Test completing a run without starting raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        with pytest.raises(InvalidStateError):
            run.complete()

    def test_fail_run(self):
        """Test failing a run."""
        run = Run(automation_id=uuid4())
        run.start()
        run.fail("error occurred")
        assert run.status == ExecutionStatus.FAILED
        assert run.error_summary == "error occurred"
        assert run.finished_at is not None

    def test_cancel_run(self):
        """Test cancelling a run."""
        run = Run(automation_id=uuid4())
        run.start()
        run.cancel("cancelled by user")
        assert run.status == ExecutionStatus.CANCELLED
        assert run.cancellation_reason == "cancelled by user"
        assert run.finished_at is not None

    def test_cancel_completed_run_raises(self):
        """Test cancelling a completed run raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        run.start()
        run.complete()
        with pytest.raises(InvalidStateError):
            run.cancel("reason")

    def test_fail_already_finished_raises(self):
        """Test failing a completed run raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        run.start()
        run.complete()
        with pytest.raises(InvalidStateError):
            run.fail("error")


class TestBatchExecution:
    """Test suite for BatchExecution entity."""
    def test_create_batch_execution(self):
        """Test batch execution creation with run_id and batch_id."""
        run_id = uuid4()
        batch_id = uuid4()
        be = BatchExecution(run_id=run_id, batch_id=batch_id)
        assert be.run_id == run_id
        assert be.batch_id == batch_id
        assert be.status == ExecutionStatus.PENDING

    def test_start_batch_execution(self):
        """Test starting a batch execution."""
        be = BatchExecution(run_id=uuid4(), batch_id=uuid4())
        be.start()
        assert be.status == ExecutionStatus.PROCESSING
        assert be.started_at is not None

    def test_complete_batch_execution(self):
        """Test completing a batch execution."""
        be = BatchExecution(run_id=uuid4(), batch_id=uuid4())
        be.start()
        be.complete()
        assert be.status == ExecutionStatus.COMPLETED
        assert be.finished_at is not None

    def test_fail_batch_execution(self):
        """Test failing a batch execution."""
        be = BatchExecution(run_id=uuid4(), batch_id=uuid4())
        be.start()
        be.fail()
        assert be.status == ExecutionStatus.FAILED
        assert be.finished_at is not None


class TestItemExecution:
    """Test suite for ItemExecution entity (comprehensive)."""
    def test_create_item_execution(self):
        """Test item execution creation with required IDs."""
        run_id = uuid4()
        batch_execution_id = uuid4()
        item_id = uuid4()
        ie = ItemExecution(run_id=run_id, batch_execution_id=batch_execution_id, item_id=item_id)
        assert ie.run_id == run_id
        assert ie.batch_execution_id == batch_execution_id
        assert ie.item_id == item_id
        assert ie.status == ExecutionStatus.PENDING
        assert ie.attempt_count == 0
        assert ie.max_attempts is None

    def test_create_with_max_attempts(self):
        """Test creating with max_attempts set."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=3)
        assert ie.max_attempts == 3

    def test_create_negative_max_attempts_raises(self):
        """Test that negative max_attempts raises ValidationError."""
        with pytest.raises(ValidationError):
            ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=-1)

    def test_start_item_execution(self):
        """Test starting an item execution."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        assert ie.status == ExecutionStatus.PROCESSING
        assert ie.started_at is not None
        assert ie.attempt_count == 1

    def test_start_when_max_attempts_reached_raises(self):
        """Test that starting when attempt count equals max_attempts raises InvalidStateError."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=2)
        ie.start()
        ie.status = ExecutionStatus.PENDING
        ie.start()
        ie.status = ExecutionStatus.PENDING
        with pytest.raises(InvalidStateError):
            ie.start()

    def test_complete_item_execution(self):
        """Test completing an item execution with result payload."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        ie.complete(result_payload={"output": "success"})
        assert ie.status == ExecutionStatus.COMPLETED
        assert ie.result_payload == {"output": "success"}
        assert ie.finished_at is not None

    def test_fail_when_retries_remaining_transitions_to_retrying(self):
        """Test that fail when attempts remain transitions to RETRYING."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=3)
        ie.start()
        ie.fail("temporary error")
        assert ie.status == ExecutionStatus.RETRYING
        assert ie.error_message == "temporary error"
        assert ie.finished_at is None
        assert ie.attempt_count == 1

    def test_fail_when_no_retries_remaining_transitions_to_failed(self):
        """Test that fail after max attempts transitions to FAILED."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=2)
        ie.start()
        ie.fail("first fail")
        ie.start()
        ie.fail("second fail")
        assert ie.status == ExecutionStatus.FAILED
        assert ie.error_message == "second fail"
        assert ie.finished_at is not None

    def test_fail_when_max_attempts_none_transitions_to_failed(self):
        """Test that fail when max_attempts is None transitions directly to FAILED."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        ie.fail("error")
        assert ie.status == ExecutionStatus.FAILED
        assert ie.finished_at is not None

    def test_can_retry_true_when_attempts_remaining(self):
        """Test can_retry returns True when attempts left."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=3)
        ie.attempt_count = 1
        assert ie.can_retry() is True

    def test_can_retry_false_when_max_attempts_none(self):
        """Test can_retry returns False when max_attempts is None."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        assert ie.can_retry() is False

    def test_can_retry_false_when_attempts_equal_max(self):
        """Test can_retry returns False when attempts equal max_attempts."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4(), max_attempts=3)
        ie.attempt_count = 3
        assert ie.can_retry() is False

    def test_start_completed_item_execution_raises(self):
        """Test that starting a completed item execution raises InvalidStateError."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        ie.complete()
        with pytest.raises(InvalidStateError):
            ie.start()

    def test_item_execution_missing_run_id_raises(self):
        """Test that missing run_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ItemExecution(run_id=None, batch_execution_id=uuid4(), item_id=uuid4())

    def test_item_execution_missing_batch_execution_id_raises(self):
        """Test that missing batch_execution_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ItemExecution(run_id=uuid4(), batch_execution_id=None, item_id=uuid4())

    def test_item_execution_missing_item_id_raises(self):
        """Test that missing item_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=None)

    def test_fail_when_already_completed_raises(self):
        """Test that failing a completed item execution raises InvalidStateError."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        ie.complete()
        with pytest.raises(InvalidStateError):
            ie.fail("error")

    def test_register_event_on_fail(self):
        """Test that failing emits an ItemExecutionFailed event."""
        ie = ItemExecution(run_id=uuid4(), batch_execution_id=uuid4(), item_id=uuid4())
        ie.start()
        ie.fail("error")
        events = ie.pop_events()
        assert len(events) > 0
        assert events[0].__class__.__name__ == "ItemExecutionFailed"
