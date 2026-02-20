import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and session management.

    Manages connection pooling and provides a session factory.
    All parameters must be provided explicitly at instantiation.

    Attributes:
        database_url (str): PostgreSQL connection string.
        pool_size (int): Size of the connection pool.
        max_overflow (int): Maximum overflow connections.
        engine_kwargs (Dict[str, Any]): Additional keyword args for create_engine.
        engine (Engine): SQLAlchemy engine instance.
        SessionLocal (sessionmaker): Session factory.
    """
    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        engine_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """Initialize database configuration.

        Args:
            database_url (str): PostgreSQL connection string (required).
            pool_size (int, optional): Size of the connection pool. Defaults to 5.
            max_overflow (int, optional): Maximum overflow connections. Defaults to 10.
            engine_kwargs (Optional[Dict[str, Any]], optional): Additional keyword arguments
                passed to `create_engine`. Defaults to None.

        Raises:
            ValueError: If database_url is empty.
        """
        if not database_url:
            raise ValueError("database_url must be provided")

        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.engine_kwargs = engine_kwargs or {}

        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        logger.info("Database engine created for %s", self.database_url)

    def _create_engine(self):
        """Create the SQLAlchemy engine with configured pooling.

        Returns:
            Engine: SQLAlchemy engine instance.
        """
        return create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            **self.engine_kwargs,
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session. Use as a context manager.

        Example:
            with db_config.get_session() as session:
                session.execute(...)

        Yields:
            Session: SQLAlchemy session.

        Raises:
            Exception: Any exception triggers a rollback.
        """
        db = self.SessionLocal()
        try:
            logger.debug("Database session opened")
            yield db
        except Exception:
            db.rollback()
            logger.exception("Rolling back session due to exception")
            raise
        finally:
            db.close()
            logger.debug("Database session closed")

    def dispose_engine(self) -> None:
        """Dispose the connection pool (e.g., on application shutdown)."""
        self.engine.dispose()
        logger.info("Database engine disposed")
