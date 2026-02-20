from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.project.domain.entities.definition import Automation
from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.infrastructure.exceptions.repository import (
    DuplicateEntityError,
    RepositoryError,
    EntityNotFoundError,
    ConcurrencyError,
)
from tests.conftest import UoWHelper


class TestBaseRepositoryConcurrency:
    """Test concurrency handling in BaseRepository."""
    def test_concurrent_update_raises_concurrency_error(self, engine):
        """Test that concurrent updates with versioning enabled raise ConcurrencyError."""
        original_versioning = AutomationRepository.use_versioning
        AutomationRepository.use_versioning = True
        try:
            session1 = Session(bind=engine)
            uow1 = UoWHelper(session1)
            repo1 = AutomationRepository(session1, uow1)
            auto = Automation(name="concurrent-test")
            created = repo1.create(auto)
            uow1.commit()

            session2 = Session(bind=engine)
            uow2 = UoWHelper(session2)
            repo2 = AutomationRepository(session2, uow2)
            auto2 = repo2.get(created.id)
            auto2.name = "updated-by-session2"

            auto1 = repo1.get(created.id)
            auto1.name = "updated-by-session1"
            repo1.update(auto1.id, auto1)
            uow1.commit()

            with pytest.raises(ConcurrencyError):
                repo2.update(auto2.id, auto2)

            session2.close()
            session1.close()
        finally:
            AutomationRepository.use_versioning = original_versioning

    def test_soft_delete_with_expected_version_success(self, test_uow):
        """Test soft-delete succeeds when expected_version matches current version."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto = Automation(name="test")
        created = repo.create(auto)
        test_uow.commit()

        auto2 = repo.get(created.id)
        assert repo.delete(created.id, soft=True, expected_version=auto2.version) is True
        test_uow.commit()

        deleted = repo.get(created.id, include_soft_deleted=True)
        assert deleted.is_active is False


class TestBaseRepositoryErrorHandling:
    """Test error handling methods of BaseRepository."""
    def test_get_or_raise_raises_not_found(self, test_uow):
        """Test get_or_raise raises EntityNotFoundError for missing entity."""
        repo = AutomationRepository(test_uow.session, test_uow)
        with pytest.raises(EntityNotFoundError):
            repo.get_or_raise(uuid4())

    def test_list_with_invalid_filter_raises_repository_error(self, test_uow):
        """Test that passing an invalid filter field raises RepositoryError."""
        repo = AutomationRepository(test_uow.session, test_uow)
        with pytest.raises(RepositoryError, match="Invalid filter field"):
            repo.list(invalid_field="value")

    def test_create_duplicate_raises_duplicate_entity_error(self, test_uow):
        """Test that creating a duplicate raises DuplicateEntityError."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto1 = Automation(name="dup")
        repo.create(auto1)
        test_uow.commit()

        auto2 = Automation(name="dup")
        with pytest.raises(DuplicateEntityError):
            repo.create(auto2)
        test_uow.rollback()

    def test_refresh_untracked_entity_raises(self, test_uow):
        """Test refreshing an entity not tracked raises RepositoryError."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto = Automation(name="test")
        auto.id = uuid4()
        with pytest.raises(RepositoryError, match="Cannot refresh untracked"):
            repo.refresh(auto)

    def test_refresh_tracked_entity_updates(self, test_uow):
        """Test refreshing a tracked entity updates its state from the database."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto = Automation(name="original")
        created = repo.create(auto)
        test_uow.commit()

        test_uow.session.execute(
            text("UPDATE automation SET name='changed' WHERE id = :id"), {"id": created.id}
        )
        test_uow.session.commit()

        refreshed = repo.refresh(created)
        assert refreshed.name == "changed"

    def test_exists(self, test_uow):
        """Test exists returns True for existing entity, False otherwise."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto = Automation(name="test")
        created = repo.create(auto)
        test_uow.commit()
        assert repo.exists(created.id) is True
        assert repo.exists(uuid4()) is False

    def test_count(self, test_uow):
        """Test count returns the correct number of entities, respecting soft-delete."""
        repo = AutomationRepository(test_uow.session, test_uow)
        for i in range(3):
            auto = Automation(name=f"auto{i}")
            repo.create(auto)
        test_uow.commit()
        assert repo.count() == 3
        assert repo.count(include_soft_deleted=True) == 3

        autos = repo.list()
        repo.delete(autos[0].id, soft=True)
        test_uow.commit()
        assert repo.count() == 2
        assert repo.count(include_soft_deleted=True) == 3

    def test_soft_delete_with_stale_version_raises_concurrency(self, engine):
        """Test that soft-delete with stale version raises ConcurrencyError."""
        original_versioning = AutomationRepository.use_versioning
        AutomationRepository.use_versioning = True
        try:
            session1 = Session(bind=engine)
            uow1 = UoWHelper(session1)
            repo1 = AutomationRepository(session1, uow1)
            auto = Automation(name="test")
            created = repo1.create(auto)
            uow1.commit()
            assert created.version == 1

            session2 = Session(bind=engine)
            uow2 = UoWHelper(session2)
            repo2 = AutomationRepository(session2, uow2)
            auto2 = repo2.get(created.id)
            auto2.name = "updated"
            repo2.update(auto2.id, auto2)
            uow2.commit()
            session2.close()

            with pytest.raises(ConcurrencyError):
                repo1.delete(created.id, soft=True, expected_version=1)
            uow1.rollback()
            session1.close()
        finally:
            AutomationRepository.use_versioning = original_versioning

    def test_hard_delete_with_stale_version_raises_concurrency(self, engine):
        """Test that hard-delete with stale version raises ConcurrencyError."""
        original_versioning = AutomationRepository.use_versioning
        AutomationRepository.use_versioning = True
        try:
            session1 = Session(bind=engine)
            uow1 = UoWHelper(session1)
            repo1 = AutomationRepository(session1, uow1)
            auto = Automation(name="test")
            created = repo1.create(auto)
            uow1.commit()
            assert created.version == 1

            session2 = Session(bind=engine)
            uow2 = UoWHelper(session2)
            repo2 = AutomationRepository(session2, uow2)
            auto2 = repo2.get(created.id)
            auto2.name = "updated"
            repo2.update(auto2.id, auto2)
            uow2.commit()
            session2.close()

            with pytest.raises(ConcurrencyError):
                repo1.delete(created.id, soft=False, expected_version=1)
            uow1.rollback()
            session1.close()
        finally:
            AutomationRepository.use_versioning = original_versioning

    def test_update_with_expected_version_none_and_versioning_enabled(self, engine):
        """Test update without expected_version uses internal version when versioning enabled."""
        original_versioning = AutomationRepository.use_versioning
        AutomationRepository.use_versioning = True
        try:
            session1 = Session(bind=engine)
            uow1 = UoWHelper(session1)
            repo1 = AutomationRepository(session1, uow1)
            auto = Automation(name="test")
            created = repo1.create(auto)
            uow1.commit()

            auto = repo1.get(created.id)
            auto.name = "updated"
            repo1.update(auto.id, auto)
            uow1.commit()
        finally:
            AutomationRepository.use_versioning = original_versioning
