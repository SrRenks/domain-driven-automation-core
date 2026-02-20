from uuid import uuid4
from datetime import datetime, timezone

from src.project.domain.entities.definition import Automation


class TestDomainEntity:
    """Test suite for DomainEntity base class methods."""
    def test_touch_without_user(self):
        """Test touch() updates updated_at but not updated_by."""
        auto = Automation(name="test")
        now = datetime.now(timezone.utc)
        auto.created_at = now
        auto.updated_at = now
        auto.version = 1
        old_updated = auto.updated_at
        auto.touch()
        assert auto.updated_at > old_updated
        assert auto.updated_by is None

    def test_touch_when_already_touched(self):
        """Test multiple touches increment updated_at but not version."""
        auto = Automation(name="test")
        auto.touch()
        old_updated = auto.updated_at
        auto.touch()
        assert auto.updated_at > old_updated

    def test_touch_with_user(self):
        """Test touch(user) sets updated_by."""
        auto = Automation(name="test")
        auto.created_at = datetime.now(timezone.utc)
        auto.updated_at = datetime.now(timezone.utc)
        auto.version = 1
        auto.touch("admin")
        assert auto.updated_by == "admin"

    def test_deactivate(self):
        """Test deactivate sets is_active to False."""
        auto = Automation(name="test")
        auto.is_active = True
        auto.deactivate()
        assert auto.is_active is False

    def test_activate(self):
        """Test activate sets is_active to True."""
        auto = Automation(name="test")
        auto.is_active = False
        auto.activate()
        assert auto.is_active is True

    def test_repr(self):
        """Test __repr__ includes class name and ID."""
        auto = Automation(name="test")
        auto.id = uuid4()
        repr_str = repr(auto)
        assert "Automation" in repr_str
        assert str(auto.id) in repr_str

    def test_eq_different_id(self):
        """Test that two entities with different IDs are not equal."""
        auto1 = Automation(name="a")
        auto1.id = uuid4()
        auto2 = Automation(name="b")
        auto2.id = uuid4()
        assert auto1 != auto2

    def test_eq_non_entity(self):
        """Test that an entity is not equal to a non-entity object."""
        auto = Automation(name="test")
        auto.id = uuid4()
        assert auto != "not an entity"
