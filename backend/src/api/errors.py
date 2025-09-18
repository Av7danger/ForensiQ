""Error handlers for the API."""
from typing import Any, Dict, Optional, Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..schemas.error import ErrorResponse, ValidationErrorResponse

async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    ""Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=exc.status_code,
            request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
        ).dict(exclude_none=True),
    )

async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    ""Handle validation errors."""
    errors: Dict[str, Any] = {}
    
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            loc = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors[loc] = error["msg"]
    elif isinstance(exc, ValidationError):
        for error in exc.errors():
            loc = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors[loc] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ValidationErrorResponse(
            error="Validation Error",
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
            details=errors,
        ).dict(exclude_none=True),
    )

async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    ""Handle unhandled exceptions."""
    # Log the error
    request.app.logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request.state.request_id if hasattr(request.state, 'request_id') else None,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
        ).dict(exclude_none=True),
    )
