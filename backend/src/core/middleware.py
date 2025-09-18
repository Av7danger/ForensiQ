""Middleware for the FastAPI application."""
import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config.settings import get_settings
from ..utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class RequestIDMiddleware(BaseHTTPMiddleware):
    ""Middleware to add a unique request ID to each request."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        ""Add request ID to the request state and response headers."""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    ""Middleware to add process time to response headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        ""Add X-Process-Time header to the response."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    ""Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        ""Log request and response details."""
        # Skip logging for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                f"Request failed: {str(exc)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                },
            )
            raise
        
        # Calculate process time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )
        
        return response


def setup_middleware(app: FastAPI) -> None:
    ""Set up all middleware for the application."""
    # Trusted Hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    
    # HTTPS Redirect (only in production)
    if settings.ENVIRONMENT == "production":
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # GZip Compression
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Only compress responses > 1KB
    )
    
    # Session Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="forensiq_session",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        https_only=settings.ENVIRONMENT == "production",
        same_site="lax",
    )
    
    # Custom Middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(ProcessTimeMiddleware)
    app.add_middleware(LoggingMiddleware)
