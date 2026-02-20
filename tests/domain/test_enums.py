import pytest

from src.project.domain.enums import ExecutionStatus


@pytest.mark.parametrize(
    "from_status,to_status,expected",
    [
        (ExecutionStatus.PENDING, ExecutionStatus.PENDING, False),
        (ExecutionStatus.PENDING, ExecutionStatus.PROCESSING, True),
        (ExecutionStatus.PENDING, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.PENDING, ExecutionStatus.FAILED, False),
        (ExecutionStatus.PENDING, ExecutionStatus.CANCELLED, True),
        (ExecutionStatus.PENDING, ExecutionStatus.SKIPPED, True),
        (ExecutionStatus.PENDING, ExecutionStatus.RETRYING, False),
        (ExecutionStatus.PROCESSING, ExecutionStatus.PENDING, False),
        (ExecutionStatus.PROCESSING, ExecutionStatus.PROCESSING, False),
        (ExecutionStatus.PROCESSING, ExecutionStatus.COMPLETED, True),
        (ExecutionStatus.PROCESSING, ExecutionStatus.FAILED, True),
        (ExecutionStatus.PROCESSING, ExecutionStatus.CANCELLED, True),
        (ExecutionStatus.PROCESSING, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.PROCESSING, ExecutionStatus.RETRYING, True),
        (ExecutionStatus.COMPLETED, ExecutionStatus.PENDING, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.PROCESSING, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.COMPLETED, ExecutionStatus.RETRYING, False),
        (ExecutionStatus.FAILED, ExecutionStatus.PENDING, True),
        (ExecutionStatus.FAILED, ExecutionStatus.PROCESSING, False),
        (ExecutionStatus.FAILED, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.FAILED, ExecutionStatus.FAILED, False),
        (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.FAILED, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.FAILED, ExecutionStatus.RETRYING, True),
        (ExecutionStatus.CANCELLED, ExecutionStatus.PENDING, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.PROCESSING, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.FAILED, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.CANCELLED, ExecutionStatus.RETRYING, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.PENDING, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.PROCESSING, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.FAILED, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.SKIPPED, ExecutionStatus.RETRYING, False),
        (ExecutionStatus.RETRYING, ExecutionStatus.PENDING, False),
        (ExecutionStatus.RETRYING, ExecutionStatus.PROCESSING, True),
        (ExecutionStatus.RETRYING, ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.RETRYING, ExecutionStatus.FAILED, True),
        (ExecutionStatus.RETRYING, ExecutionStatus.CANCELLED, True),
        (ExecutionStatus.RETRYING, ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.RETRYING, ExecutionStatus.RETRYING, False),
    ],
)
def test_execution_status_transitions(from_status, to_status, expected):
    """Parameterized test for allowed transitions between ExecutionStatus values.

    Args:
        from_status (ExecutionStatus): Starting status.
        to_status (ExecutionStatus): Target status.
        expected (bool): Whether the transition should be allowed.
    """
    assert from_status.can_transition_to(to_status) == expected


def test_enum_str():
    """Test that str() on an enum member returns its name."""
    assert str(ExecutionStatus.PENDING) == "PENDING"


def test_enum_values():
    """Test that the .value attribute returns the expected string."""
    assert ExecutionStatus.PENDING.value == "PENDING"
    assert ExecutionStatus.COMPLETED.value == "COMPLETED"