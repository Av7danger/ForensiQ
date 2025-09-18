""Error response schemas."""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .base import BaseModel

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    target: Optional[str] = Field(
        None,
        description="The target of the error (e.g., field name)"
    )

class ErrorResponse(BaseModel):
    ""Standard error response model."""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracing"
    )
    details: Optional[Union[Dict[str, Any], List[ErrorDetail]]] = Field(
        None,
        description="Additional error details"
    )

class ValidationErrorResponse(ErrorResponse):
    ""Validation error response model."""
    error: str = Field(
        "Validation Error",
        description="Error message"
    )
    code: int = Field(
        422,
        description="HTTP status code"
    )
    details: Dict[str, Any] = Field(
        ...,
        description="Validation error details"
    )

class NotFoundErrorResponse(ErrorResponse):
    ""Not Found error response model."""
    error: str = Field(
        "Not Found",
        description="Error message"
    )
    code: int = Field(
        404,
        description="HTTP status code"
    )
    resource: str = Field(
        ...,
        description="The resource that was not found"
    )

class UnauthorizedErrorResponse(ErrorResponse):
    ""Unauthorized error response model."""
    error: str = Field(
        "Unauthorized",
        description="Error message"
    )
    code: int = Field(
        401,
        description="HTTP status code"
    )
    
class ForbiddenErrorResponse(ErrorResponse):
    ""Forbidden error response model."""
    error: str = Field(
        "Forbidden",
        description="Error message"
    )
    code: int = Field(
        403,
        description="HTTP status code"
    )
    permission: Optional[str] = Field(
        None,
        description="Required permission"
    )

class InternalServerErrorResponse(ErrorResponse):
    ""Internal Server Error response model."""
    error: str = Field(
        "Internal Server Error",
        description="Error message"
    )
    code: int = Field(
        500,
        description="HTTP status code"
    )
    request_id: str = Field(
        ...,
        description="Request ID for tracing"
    )
