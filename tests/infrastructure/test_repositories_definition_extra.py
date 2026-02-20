import pytest

from src.project.domain.entities.definition import Automation, Batch, Item
from src.project.infrastructure.database.repositories.definition import AutomationRepository, BatchRepository, ItemRepository


class TestAutomationRepositoryExtra:
    """Additional tests for AutomationRepository."""
    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_active_pagination(self, test_uow, limit, offset, expected):
        """Test pagination of list_active."""
        repo = AutomationRepository(test_uow.session, test_uow)
        for i in range(5):
            auto = Automation(name=f"auto{i}")
            repo.create(auto)
        test_uow.commit()
        result = repo.list_active(limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_active_soft_deleted_excluded(self, test_uow):
        """Test that list_active excludes soft-deleted automations."""
        repo = AutomationRepository(test_uow.session, test_uow)
        auto = Automation(name="test")
        repo.create(auto)
        test_uow.commit()
        repo.delete(auto.id, soft=True)
        test_uow.commit()
        assert len(repo.list_active()) == 0


class TestBatchRepositoryFilters:
    """Test filter methods of BatchRepository."""
    @pytest.mark.parametrize("limit,offset,expected_count", [(0, 0, 0), (5, 10, 0), (2, 2, 2)])
    def test_list_by_automation_pagination(self, test_uow, automation, limit, offset, expected_count):
        """Test pagination of list_by_automation."""
        repo = BatchRepository(test_uow.session, test_uow)
        for i in range(5):
            batch = Batch(automation_id=automation.id, name=f"b{i}")
            repo.create(batch)
        test_uow.commit()
        result = repo.list_by_automation(automation.id, limit=limit, offset=offset)
        assert len(result) == expected_count

    @pytest.mark.parametrize("include_soft_deleted,expected", [(False, 0), (True, 1)])
    def test_list_by_automation_include_soft_deleted(self, test_uow, automation, include_soft_deleted, expected):
        """Test include_soft_deleted flag for list_by_automation."""
        repo = BatchRepository(test_uow.session, test_uow)
        batch = Batch(automation_id=automation.id, name="b1")
        repo.create(batch)
        test_uow.commit()
        repo.delete(batch.id, soft=True)
        test_uow.commit()
        result = repo.list_by_automation(automation.id, include_soft_deleted=include_soft_deleted)
        assert len(result) == expected


class TestItemRepositoryExtra:
    """Additional tests for ItemRepository."""
    @pytest.mark.parametrize("include_soft_deleted,expected", [(False, 0), (True, 1)])
    def test_list_by_batch_include_soft_deleted(self, test_uow, batch, include_soft_deleted, expected):
        """Test include_soft_deleted for list_by_batch."""
        repo = ItemRepository(test_uow.session, test_uow)
        item = Item(batch_id=batch.id, sequence_number=1)
        repo.create(item)
        test_uow.commit()
        repo.delete(item.id, soft=True)
        test_uow.commit()
        result = repo.list_by_batch(batch.id, include_soft_deleted=include_soft_deleted)
        assert len(result) == expected

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_batch_pagination(self, test_uow, batch, limit, offset, expected):
        """Test pagination of list_by_batch."""
        repo = ItemRepository(test_uow.session, test_uow)
        for i in range(5):
            item = Item(batch_id=batch.id, sequence_number=i)
            repo.create(item)
        test_uow.commit()
        result = repo.list_by_batch(batch.id, limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_batch_pagination_edge_cases(self, test_uow, batch):
        """Test edge cases: limit=0, offset beyond total, negative offset."""
        repo = ItemRepository(test_uow.session, test_uow)
        for i in range(5):
            item = Item(batch_id=batch.id, sequence_number=i)
            repo.create(item)
        test_uow.commit()

        assert repo.list_by_batch(batch.id, limit=0) == []
        assert repo.list_by_batch(batch.id, offset=10) == []
        assert repo.list_by_batch(batch.id, offset=5) == []
        with pytest.raises(Exception, match="OFFSET must not be negative"):
            repo.list_by_batch(batch.id, offset=-1)