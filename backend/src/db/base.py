""Base database models and mixins."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression
from sqlalchemy.types import TypeDecorator, CHAR

from ..config.settings import get_settings

settings = get_settings()

class GUID(TypeDecorator):
    ""
    Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value).hex)
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value


class TimestampMixin:
    ""Mixin that adds timestamp fields to models."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class SoftDeleteMixin:
    ""Mixin that adds soft delete functionality to models."""
    
    is_deleted = Column(
        Boolean,
        server_default=expression.false(),
        nullable=False,
        default=False,
        doc="Whether the record is marked as deleted"
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the record was soft-deleted"
    )
    
    def soft_delete(self):
        ""Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()


@as_declarative()
class Base(TimestampMixin, SoftDeleteMixin):
    ""Base class for all database models."""
    
    __name__: str
    
    # Default primary key using UUID
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        unique=True,
        nullable=False,
        doc="Unique identifier for the record"
    )
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        ""Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        ""Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        ""String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
