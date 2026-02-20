from datetime import datetime, timedelta

import pytest

from src.project.infrastructure.database.mixins import StatusTrackingMixin


class TestStatusTrackingMixin:
    """Test suite for StatusTrackingMixin."""
    def test_duration_when_both_timestamps_set(self):
        """Test that duration returns the difference between started_at and finished_at."""
        class Dummy(StatusTrackingMixin):
            def __init__(self):
                self.started_at = datetime.now() - timedelta(seconds=5)
                self.finished_at = datetime.now()

        obj = Dummy()
        assert obj.duration == pytest.approx(5.0, rel=1)

    def test_duration_when_started_at_missing(self):
        """Test that duration is None if started_at is missing."""
        class Dummy(StatusTrackingMixin):
            def __init__(self):
                self.started_at = None
                self.finished_at = datetime.now()

        obj = Dummy()
        assert obj.duration is None

    def test_duration_when_finished_at_missing(self):
        """Test that duration is None if finished_at is missing."""
        class Dummy(StatusTrackingMixin):
            def __init__(self):
                self.started_at = datetime.now()
                self.finished_at = None

        obj = Dummy()
        assert obj.duration is None

    def test_duration_when_both_missing(self):
        """Test that duration is None if both timestamps are missing."""
        class Dummy(StatusTrackingMixin):
            def __init__(self):
                self.started_at = None
                self.finished_at = None

        obj = Dummy()
        assert obj.duration is None