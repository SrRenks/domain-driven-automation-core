import time
from uuid import uuid4

from sqlalchemy.orm import Session

from src.project.infrastructure.database.models.definition.automation import AutomationModel


def test_timestamp_mixin(db_session, engine):
    """Test that TimestampMixin automatically updates updated_at on modification."""
    model = AutomationModel(id=uuid4(), name="test", version=1)
    db_session.add(model)
    db_session.commit()
    original_updated = model.updated_at

    time.sleep(1)

    with Session(engine) as new_session:
        model2 = new_session.get(AutomationModel, model.id)
        model2.name = "new"
        new_session.commit()
        new_session.refresh(model2)
        assert model2.updated_at > original_updated
        assert model2.name == "new"


def test_audit_mixin(db_session):
    """Test that AuditMixin stores created_by and updated_by correctly."""
    model = AutomationModel(
        id=uuid4(),
        name="audit",
        version=1,
        created_by="tester",
        updated_by="tester",
    )
    db_session.add(model)
    db_session.flush()
    assert model.created_by == "tester"
    assert model.updated_by == "tester"


def test_version_mixin(db_session):
    """Test that VersionMixin handles version increments."""
    model = AutomationModel(id=uuid4(), name="version", version=1)
    db_session.add(model)
    db_session.flush()
    assert model.version == 1
    model.version += 1
    db_session.flush()
    assert model.version == 2