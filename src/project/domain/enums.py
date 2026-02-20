from enum import Enum
from typing import Set, Dict


class ExecutionStatus(str, Enum):
    """Enumeration of possible execution states for runs, batches, items, and orchestration instances.

    Provides properties to query state and a method to validate transitions.

    Values:
        PENDING: Not yet started.
        PROCESSING: Currently executing.
        COMPLETED: Successfully finished.
        FAILED: Finished with error.
        CANCELLED: Aborted before completion.
        SKIPPED: Not executed (e.g., due to condition).
        RETRYING: Will be retried.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    @property
    def is_finished(self) -> bool:
        """Check if status is a final (terminal) state.

        Returns:
            bool: True if status is COMPLETED, FAILED, CANCELLED, or SKIPPED.
        """
        finished_states = {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.SKIPPED
        }
        return self in finished_states

    @property
    def is_active(self) -> bool:
        """Check if execution is still active (not finished).

        Returns:
            bool: True if status is PENDING, PROCESSING, or RETRYING.
        """
        active_states = {
            ExecutionStatus.PENDING,
            ExecutionStatus.PROCESSING,
            ExecutionStatus.RETRYING
        }
        return self in active_states

    @property
    def is_running(self) -> bool:
        """Check if execution is currently running (for repository queries).

        Returns:
            bool: True if status is PROCESSING or RETRYING.
        """
        running_states = {ExecutionStatus.PROCESSING, ExecutionStatus.RETRYING}
        return self in running_states

    def can_transition_to(self, new_status: 'ExecutionStatus') -> bool:
        """Determine if a transition to new_status is allowed from the current state.

        Args:
            new_status (ExecutionStatus): The target status.

        Returns:
            bool: True if transition is allowed according to the state matrix.
        """
        valid_transitions: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
            ExecutionStatus.PENDING: {ExecutionStatus.PROCESSING, ExecutionStatus.CANCELLED, ExecutionStatus.SKIPPED},
            ExecutionStatus.PROCESSING: {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.RETRYING, ExecutionStatus.CANCELLED},
            ExecutionStatus.RETRYING: {ExecutionStatus.PROCESSING, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED},
            ExecutionStatus.COMPLETED: set(),
            ExecutionStatus.FAILED: {ExecutionStatus.PENDING, ExecutionStatus.RETRYING},
            ExecutionStatus.CANCELLED: set(),
            ExecutionStatus.SKIPPED: set(),
        }
        return new_status in valid_transitions.get(self, set())
