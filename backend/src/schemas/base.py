""Base schemas for the application."""
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic.generics import GenericModel

# Generic type for paginated results
T = TypeVar('T')

class ResponseStatus(str, Enum):
    """Response status values."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        orm_mode = True
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True

class BaseResponse(GenericModel, Generic[T]):
    """Base response model for API responses."""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
