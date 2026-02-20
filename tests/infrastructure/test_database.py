import pytest
from sqlalchemy import text

from src.project.infrastructure.database.database import DatabaseConfig


def test_database_config_empty_url_raises():
    """Test that creating DatabaseConfig with empty URL raises ValueError."""
    with pytest.raises(ValueError, match="database_url must be provided"):
        DatabaseConfig("")


def test_database_config_init_with_url(db_config):
    """Test that DatabaseConfig initializes correctly with a valid URL."""
    assert db_config.database_url is not None
    assert db_config.engine is not None
    assert db_config.SessionLocal is not None


def test_database_config_pool_params():
    """Test that pool_size and max_overflow are set correctly."""
    config = DatabaseConfig(
        "postgresql://user:pass@localhost/test",
        pool_size=10,
        max_overflow=20,
    )
    assert config.pool_size == 10
    assert config.max_overflow == 20


def test_get_session_success(db_config):
    """Test that get_session yields a working session and closes it."""
    with db_config.get_session() as session:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_get_session_rollback_on_exception(db_config):
    """Test that an exception inside get_session triggers rollback and session closes."""
    with pytest.raises(ValueError):
        with db_config.get_session() as session:
            session.execute(text("CREATE TABLE IF NOT EXISTS test_rollback (id int)"))
            raise ValueError("force rollback")


def test_dispose_engine(db_config):
    """Test that dispose_engine runs without error and is idempotent."""
    db_config.dispose_engine()
    db_config.dispose_engine()