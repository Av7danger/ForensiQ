""Enhanced database session management with connection pooling and retry logic."""
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator, Optional, Type, TypeVar, Union

from sqlalchemy import create_engine, exc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from ..config.settings import get_settings
from ..utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Type variables for better type hints
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class DatabaseManager:
    ""Enhanced database connection and session management."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[scoped_session] = None
        self._setup_database()
    
    def _setup_database(self) -> None:
        ""Initialize the database engine and session factory."""
        try:
            # Configure connection pool
            self.engine = create_engine(
                str(settings.SQLALCHEMY_DATABASE_URI),
                poolclass=QueuePool,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=settings.DB_POOL_PRE_PING,
                connect_args={
                    "connect_timeout": settings.DB_CONNECT_TIMEOUT,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                },
                echo=settings.SQL_ECHO,
            )
            
            # Create session factory
            self.session_factory = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine,
                    expire_on_commit=False,
                )
            )
            
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self) -> Session:
        ""Get a new database session."""
        if not self.session_factory:
            raise RuntimeError("Database session factory not initialized")
        return self.session_factory()
    
    def close(self) -> None:
        ""Close all connections in the connection pool."""
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        ""Provide a transactional scope around a series of operations."""
        if not self.session_factory:
            raise RuntimeError("Database session factory not initialized")
            
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def with_retry(
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        exceptions: tuple[Type[Exception], ...] = (
            exc.OperationalError,
            exc.TimeoutError,
            exc.InternalError,
        ),
    ) -> Callable[[F], F]:
        ""
        Decorator for retrying database operations with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor for exponential backoff
            exceptions: Tuple of exceptions to catch and retry on
            
        Returns:
            Decorated function with retry logic
        """
        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries - 1:
                            logger.error(
                                f"Database operation failed after {max_retries} attempts: {e}"
                            )
                            raise
                        
                        # Calculate backoff time with exponential backoff
                        backoff = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {backoff:.2f} seconds... Error: {e}"
                        )
                        time.sleep(backoff)
                
                # This should never be reached due to the raise in the except block
                raise last_exception  # type: ignore
            
            return wrapper  # type: ignore
        return decorator

# Initialize the database manager
db_manager = DatabaseManager()

def get_db() -> Generator[Session, None, None]:
    ""Dependency for getting database session."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def get_db_session() -> Session:
    ""Get a database session directly."""
    return db_manager.get_session()

@contextmanager
def session_scope() -> Generator[Session, None, None]:
    ""Context manager for database sessions."""
    with db_manager.session_scope() as session:
        yield session

def close_db_connection() -> None:
    ""Close all database connections."""
    db_manager.close()
