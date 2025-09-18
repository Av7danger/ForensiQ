""Enhanced response handling and formatting for API endpoints."""
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.generics import GenericModel

from ..schemas.base import BaseResponse, ResponseStatus
from ..schemas.error import ErrorResponse

T = TypeVar('T')

class PaginationMeta(BaseModel):
    ""Pagination metadata for paginated responses."""
    total: int
    page: int
    size: int
    total_pages: int

class PaginatedResponse(GenericModel, Generic[T]):
    ""Generic paginated response model."""
    items: List[T]
    meta: PaginationMeta

class ApiResponse(GenericModel, Generic[T]):
    ""Standard API response format."""
    status: str
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

class ResponseBuilder:
    ""Builder for consistent API responses."""
    
    @staticmethod
    def success(
        data: Any = None,
        status_code: int = status.HTTP_200_OK,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        ""Create a successful API response."""
        response = {
            "status": ResponseStatus.SUCCESS,
            "data": jsonable_encoder(data) if data is not None else None,
            "message": message,
            "meta": meta,
        }
        return JSONResponse(
            content=response,
            status_code=status_code,
        )
    
    @staticmethod
    def error(
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        ""Create an error API response."""
        response = {
            "status": ResponseStatus.ERROR,
            "error": {
                "code": error_code or f"ERR_{status_code}",
                "message": message,
                "details": details or {},
            },
        }
        return JSONResponse(
            content=response,
            status_code=status_code,
        )
    
    @staticmethod
    def not_found(
        resource: str,
        id: Optional[Union[str, int]] = None,
    ) -> JSONResponse:
        ""Create a 404 Not Found response."""
        message = f"{resource} not found"
        if id is not None:
            message += f" with id {id}"
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )
    
    @staticmethod
    def unauthorized(
        message: str = "Not authenticated",
    ) -> JSONResponse:
        ""Create a 401 Unauthorized response."""
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )
    
    @staticmethod
    def forbidden(
        message: str = "Insufficient permissions",
    ) -> JSONResponse:
        ""Create a 403 Forbidden response."""
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )
    
    @staticmethod
    def validation_error(
        errors: List[Dict[str, Any]],
    ) -> JSONResponse:
        ""Create a 422 Validation Error response."""
        return ResponseBuilder.error(
            message="Validation error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"errors": errors},
        )
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        size: int,
        **meta: Any,
    ) -> JSONResponse:
        ""Create a paginated response."""
        total_pages = (total + size - 1) // size if size > 0 else 1
        pagination_meta = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            **meta,
        }
        return ResponseBuilder.success(
            data=items,
            meta=pagination_meta,
        )

# Helper functions
def create_response(
    data: Any = None,
    status_code: int = status.HTTP_200_OK,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    ""Create a standard API response."""
    return ResponseBuilder.success(
        data=data,
        status_code=status_code,
        message=message,
        meta=meta,
    )

def create_error(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    ""Create an error API response."""
    return ResponseBuilder.error(
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details,
    )

def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    size: int,
    **meta: Any,
) -> JSONResponse:
    ""Create a paginated API response."""
    return ResponseBuilder.paginated(
        items=items,
        total=total,
        page=page,
        size=size,
        **meta,
    )
