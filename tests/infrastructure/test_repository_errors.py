from uuid import uuid4

import pytest

from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.infrastructure.database.repositories.execution import RunRepository
from src.project.domain.entities import Automation, Run
from src.project.infrastructure.exceptions.repository import DuplicateEntityError, RepositoryError


def test_unique_constraint_violation(db_session, uow_mock):
    """Test that creating a duplicate entity raises DuplicateEntityError."""
    repo = AutomationRepository(db_session, uow_mock)
    auto = Automation(name="unique")
    repo.create(auto)
    auto2 = Automation(name="unique")
    with pytest.raises(DuplicateEntityError):
        repo.create(auto2)


def test_foreign_key_violation(db_session, uow_mock):
    """Test that creating an entity with a non-existent foreign key raises RepositoryError."""
    repo = RunRepository(db_session, uow_mock)
    run = Run(automation_id=uuid4())
    with pytest.raises(RepositoryError, match="Integrity error.*foreign key"):
        repo.create(run)