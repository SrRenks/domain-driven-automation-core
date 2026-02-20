from uuid import uuid4

import pytest

from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.domain.entities import Automation
from src.project.infrastructure.exceptions.repository import RepositoryError


def test_list_with_filters(db_session, uow_mock):
    """Test that list() filters results correctly based on keyword arguments."""
    repo = AutomationRepository(db_session, uow_mock)
    auto1 = Automation(name="filter1", description="desc1")
    auto2 = Automation(name="filter2", description="desc2")
    repo.create(auto1)
    repo.create(auto2)

    results = repo.list(name="filter1")
    assert len(results) == 1
    assert results[0].name == "filter1"

    results = repo.list(description="desc2")
    assert len(results) == 1
    assert results[0].description == "desc2"

    results = repo.list(name="filter1", description="desc1")
    assert len(results) == 1

    results = repo.list(name="nonexistent")
    assert len(results) == 0


def test_list_invalid_filter_field(db_session, uow_mock):
    """Test that passing an invalid field name raises RepositoryError."""
    repo = AutomationRepository(db_session, uow_mock)
    with pytest.raises(RepositoryError, match="Invalid filter field"):
        repo.list(nonexistent_field="value")


def test_exists(db_session, uow_mock):
    """Test the exists() method."""
    repo = AutomationRepository(db_session, uow_mock)
    auto = Automation(name="exists")
    created = repo.create(auto)
    assert repo.exists(created.id) is True
    assert repo.exists(uuid4()) is False


def test_count(db_session, uow_mock):
    """Test the count() method with and without filters."""
    repo = AutomationRepository(db_session, uow_mock)
    repo.create(Automation(name="count1"))
    repo.create(Automation(name="count2"))
    assert repo.count() == 2
    assert repo.count(name="count1") == 1


def test_soft_delete_filtering(db_session, uow_mock):
    """Test that soft-deleted entities are excluded by default but can be included."""
    repo = AutomationRepository(db_session, uow_mock)
    auto = Automation(name="soft")
    created = repo.create(auto)
    repo.delete(created.id, soft=True)
    assert repo.get(created.id) is None

    soft = repo.get(created.id, include_soft_deleted=True)
    assert soft is not None
    assert soft.is_active is False
    assert len(repo.list()) == 0
    assert len(repo.list(include_soft_deleted=True)) == 1
    assert repo.count() == 0
    assert repo.count(include_soft_deleted=True) == 1