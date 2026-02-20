from uuid import uuid4

import pytest

from src.project.domain.entities import Run, ItemExecution
from src.project.domain.enums import ExecutionStatus
from src.project.domain.events import DomainEvent, RunCompleted
from src.project.domain.exceptions import InvalidStateError


class TestRunStateTransitions:
    """Test state transitions for Run entity."""
    def test_start_transition(self):
        """Test transition from PENDING to PROCESSING."""
        run = Run(automation_id=uuid4())
        assert run.status == ExecutionStatus.PENDING
        events_before = list(run.pop_events())
        assert len(events_before) == 0

        run.start()
        assert run.status == ExecutionStatus.PROCESSING
        assert run.started_at is not None
        assert run.version == 2

    def test_complete_from_processing(self):
        """Test transition from PROCESSING to COMPLETED and event emission."""
        run = Run(automation_id=uuid4())
        run.start()
        run.complete()
        assert run.status == ExecutionStatus.COMPLETED
        assert run.finished_at is not None
        events = run.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], RunCompleted)

    def test_fail_from_processing(self):
        """Test transition from PROCESSING to FAILED and event emission."""
        run = Run(automation_id=uuid4())
        run.start()
        run.fail("error summary")
        assert run.status == ExecutionStatus.FAILED
        assert run.error_summary == "error summary"
        events = run.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], DomainEvent)

    def test_cancel_from_processing(self):
        """Test transition from PROCESSING to CANCELLED and event emission."""
        run = Run(automation_id=uuid4())
        run.start()
        run.cancel("user request")
        assert run.status == ExecutionStatus.CANCELLED
        assert run.cancellation_reason == "user request"
        events = run.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], DomainEvent)

    def test_complete_from_pending_raises(self):
        """Test that completing from PENDING raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        with pytest.raises(InvalidStateError):
            run.complete()

    def test_fail_from_pending_raises(self):
        """Test that failing from PENDING raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        with pytest.raises(InvalidStateError):
            run.fail("reason")

    def test_cancel_from_pending_raises(self):
        """Test that cancelling from PENDING is allowed (CANCELLED is a terminal state)."""
        run = Run(automation_id=uuid4())
        run.cancel("reason")
        assert run.status == ExecutionStatus.CANCELLED
        assert run.cancellation_reason == "reason"

    def test_start_twice_raises(self):
        """Test that starting a run twice raises InvalidStateError."""
        run = Run(automation_id=uuid4())
        run.start()
        with pytest.raises(InvalidStateError):
            run.start()


class TestItemExecutionRetry:
    """Test retry behavior for ItemExecution."""
    def test_start_increments_attempt(self):
        """Test that start increments attempt_count."""
        item = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=3,
        )
        assert item.attempt_count == 0
        item.start()
        assert item.attempt_count == 1
        assert item.status == ExecutionStatus.PROCESSING

    def test_fail_with_remaining_attempts_sets_retrying(self):
        """Test that fail when attempts remain sets status to RETRYING."""
        item = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=3,
        )
        item.start()
        item.fail("timeout")
        assert item.status == ExecutionStatus.RETRYING
        assert item.attempt_count == 1
        assert item.can_retry() is True

    def test_fail_exhausts_attempts_sets_failed(self):
        """Test that fail after max attempts sets status to FAILED."""
        item = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=1,
        )
        item.start()
        item.fail("fatal")
        assert item.status == ExecutionStatus.FAILED
        assert item.can_retry() is False

    def test_can_retry_logic(self):
        """Test can_retry returns correct boolean based on attempts and max_attempts."""
        item = ItemExecution(
            run_id=uuid4(),
            batch_execution_id=uuid4(),
            item_id=uuid4(),
            max_attempts=2,
        )
        assert item.can_retry() is True
        item.start()
        item.fail("msg")
        assert item.can_retry() is True
        item.start()
        item.fail("msg again")
        assert item.can_retry() is False

        with pytest.raises(InvalidStateError):
            item.start()
