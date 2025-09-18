# backend/main.py
"""
Core API for ForensiQ digital forensics platform
Author: Backend Engineer
Python 3.11+

Main FastAPI application entry point with core endpoints.
"""

import asyncio
import gzip
import json
import logging
import time
import uuid
import os
from typing import Any, Callable, Dict, Optional, Tuple, Union
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import (
    FastAPI, 
    Request, 
    Response, 
    status, 
    Depends, 
    HTTPException,
    BackgroundTasks,
    Security,
    Header
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, HttpUrl, validator
from pydantic.error_wrappers import ValidationError as PydanticValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.slowapi import SlowAPIMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.database import init_db, get_db
from app.api.v1 import api_router

# Constants
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
LOG_FILE = "logs/forensiq.log"
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))  # 100MB default
API_PREFIX = "/api/v1"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
API_VERSION = "1.0.0"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

class RequestIdFilter(logging.Filter):
    """Add request_id to log records"""
    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = 'system'
        return True

# Configure root logger
logging.basicConfig(level=logging.ERROR)

# Configure application logger
logger = logging.getLogger("forensiq")
logger.setLevel(LOG_LEVEL)
logger.addFilter(RequestIdFilter())

# Create formatters and handlers
formatter = logging.Formatter(LOG_FORMAT)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Disable noisy loggers
for log_name in ["uvicorn", "uvicorn.error", "fastapi"]:
    logging.getLogger(log_name).handlers = []
    logging.getLogger(log_name).propagate = True

# Set log levels for specific loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Add JSON formatter for production
if IS_PRODUCTION:
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'logger': record.name,
                'request_id': getattr(record, 'request_id', 'system'),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'thread': record.thread,
                'process': record.process
            }
            if record.exc_info:
                log_record['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_record)
    
    json_formatter = JsonFormatter()
    for handler in logger.handlers:
        handler.setFormatter(json_formatter)

# Rate limiting
rate_limit = RATE_LIMIT
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[rate_limit],
    headers_enabled=True,
    storage_uri="memory://"
)

# Security
security = HTTPBearer(
    auto_error=False,
    scheme_name="JWT",
    description="Enter JWT token in the format: `Bearer <token>`",
    bearerFormat="JWT"
)

# Trusted hosts
TRUSTED_HOSTS = os.getenv("TRUSTED_HOSTS", "*").split(",")

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: Optional[str] = Field(None, description="Request path")
    method: Optional[str] = Field(None, description="HTTP method")

    class Config:
        schema_extra = {
            "example": {
                "error": "Resource not found",
                "code": 404,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-09-19T00:00:00Z"
            }
        }

class ValidationErrorResponse(ErrorResponse):
    """Validation error response model"""
    details: dict = Field(..., description="Validation error details")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Validation Error",
                "code": 422,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-09-19T00:00:00Z",
                "details": [
                    {
                        "loc": ["string", 0],
                        "msg": "string",
                        "type": "string"
                    }
                ]
            }
        }

class SuccessResponse(BaseModel):
    """Standard success response model"""
    status: str = "success"
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = {}
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {"key": "value"},
                "meta": {"count": 1}
            }
        }

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request: Request = None
) -> str:
    """
    Verify JWT token from Authorization header.
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
        request: The incoming request object
        
    Returns:
        str: The authenticated user ID from the token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        logger.warning("No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # TODO: Implement actual JWT token verification
        # This is a placeholder that should be replaced with proper JWT validation
        # Example:
        # payload = jwt.decode(
        #     token,
        #     settings.SECRET_KEY,
        #     algorithms=[settings.JWT_ALGORITHM],
        #     options={"verify_aud": False}
        # )
        # return payload.get("sub")
        
        # For now, just log and return a mock user ID
        logger.info(f"Token verified for user: mock-user")
        return "mock-user"
        
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan with startup and shutdown events.
    
    Handles initialization and cleanup of resources.
    """
    startup_time = time.time()
    
    # Startup
    logger.info("""
    ============================================
    Starting ForensiQ API
    Environment: %s
    Version: %s
    ============================================
    """, ENVIRONMENT, API_VERSION)
    
    # Initialize database
    logger.info("Initializing database connection...")
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.critical(f"❌ Failed to initialize database: {str(e)}", exc_info=True)
        raise
    
    # Log startup completion
    startup_duration = time.time() - startup_time
    logger.info(f"🚀 Application startup completed in {startup_duration:.2f} seconds")
    
    # Yield control to the application
    yield
    
    # Shutdown
    logger.info("""
    ============================================
    Shutting down ForensiQ API...
    ============================================
    """)
    
    # Add any cleanup code here
    # Example: Close database connections, release resources, etc.
    try:
        # Close database connections
        from app.database import SessionLocal
        SessionLocal.remove()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}", exc_info=True)
    
    logger.info("👋 Application shutdown complete")

def custom_openapi():
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Customize the OpenAPI schema
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token in the format: `Bearer <token>`"
        }
    }
    
    # Add security requirements to all paths
    for path in openapi_schema["paths"].values():
        for method in path.values():
            if method.get("security") is None:
                method["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Initialize FastAPI app with lifespan events
app = FastAPI(
    title="ForensiQ API",
    description="""
    ## ForensiQ - Digital Forensics Platform
    
    Secure and efficient API for digital forensics investigations.
    
    ### Features:
    - Case management
    - Evidence tracking
    - Secure file handling
    - Audit logging
    - Advanced search capabilities
    - User authentication and authorization
    - Role-based access control
    - Audit trails
    - Data export
    
    ### Authentication
    This API uses JWT for authentication. Include the token in the `Authorization` header as `Bearer <token>`.
    """,
    version=API_VERSION,
    docs_url=None,  # Custom docs endpoints
    redoc_url=None,  # Custom ReDoc endpoint
    openapi_url=f"{API_PREFIX}/openapi.json" if IS_PRODUCTION else "/openapi.json",
    contact={
        "name": "ForensiQ Support",
        "email": "support@forensiq.example.com",
        "url": "https://forensiq.example.com/support"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://forensiq.example.com/license"
    },
    terms_of_service="https://forensiq.example.com/terms",
    lifespan=lifespan,
    debug=not IS_PRODUCTION,
    root_path=os.getenv("ROOT_PATH", ""),
    root_path_in_servers=False,
    servers=[
        {"url": "/", "description": "Current server"},
        {"url": "https://api.forensiq.example.com", "description": "Production server"},
        {"url": "https://staging.forensiq.example.com", "description": "Staging server"},
    ]
)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Custom docs endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        with_google_fonts=False,
    )

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middlewares in the correct order
# 1. TrustedHostMiddleware - First to reject invalid hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS if "*" not in TRUSTED_HOSTS else ["*"],
)

# 2. HTTPS Redirect - Only in production
if IS_PRODUCTION:
    app.add_middleware(HTTPSRedirectMiddleware)

# 3. GZip - Compress responses
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=6,    # Balance between speed and compression ratio
)

# 4. CORS - Handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Length",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Process-Time",
        "X-Cache-Hit",
    ],
    max_age=600,  # 10 minutes
)

# 5. Session Middleware - For session management
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-to-a-secure-secret"),
    session_cookie="forensiq_session",
    max_age=3600 * 24 * 7,  # 7 days
    https_only=True,
    same_site="lax",
)

# 6. Rate Limiting - Protect against abuse
app.add_middleware(SlowAPIMiddleware)

# 7. Request ID - Add unique ID to each request
class RequestIdMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Add request ID to logs
        record_factory = logging.getLogRecordFactory()
        
        def record_factory_with_request_id(*args, **kwargs):
            record = record_factory(*args, **kwargs)
            record.request_id = request_id
            return record
            
        logging.setLogRecordFactory(record_factory_with_request_id)
        
        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start" and "headers" in message:
                headers = message["headers"]
                headers.append([b"x-request-id", request_id.encode()])
            await send(message)
        
        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as e:
            logger.error(f"Request failed: {str(e)}", exc_info=True)
            raise

app.add_middleware(RequestIdMiddleware)

# 8. Logging Middleware - Log all requests and responses
class LoggingMiddleware:
    async def __call__(self, request: Request, call_next):
        # Skip logging for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Log request
        request_id = request.state.request_id
        logger.info(
            f"Request: {request.method} {request.url} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request and time it
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Process Time: {process_time:.2f}ms"
        )
        
        return response

app.middleware("http")(LoggingMiddleware())

# 9. Security Headers Middleware
class SecurityHeadersMiddleware:
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "font-src 'self' cdn.jsdelivr.net; "
                "connect-src 'self';",
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-site",
            "X-Permitted-Cross-Domain-Policies": "none",
        }
        
        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response

app.middleware("http")(SecurityHeadersMiddleware())

# 10. Request Validation Middleware
class RequestValidationMiddleware:
    async def __call__(self, request: Request, call_next):
        # Skip validation for certain paths
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Validate content type for JSON requests
        content_type = request.headers.get("content-type", "")
        if request.method in ["POST", "PUT", "PATCH"] and "application/json" in content_type:
            try:
                body = await request.json()
                request.state.parsed_body = body
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Invalid JSON",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "request_id": request.state.request_id,
                    },
                )
        
        return await call_next(request)

app.middleware("http")(RequestValidationMiddleware())

# 11. Timeout Middleware
class TimeoutMiddleware:
    async def __call__(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request.method} {request.url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "code": status.HTTP_504_GATEWAY_TIMEOUT,
                    "request_id": request.state.request_id,
                },
            )

app.middleware("http")(TimeoutMiddleware())

# 12. Size Limit Middleware
class SizeLimitMiddleware:
    async def __call__(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": f"Payload too large. Maximum size is {MAX_UPLOAD_SIZE} bytes",
                    "code": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    "request_id": request.state.request_id,
                    "max_size": MAX_UPLOAD_SIZE,
                },
            )
        return await call_next(request)

app.middleware("http")(SizeLimitMiddleware())

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else str(uuid.uuid4())
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.status_code,
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else str(uuid.uuid4())
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "request_id": request_id,
            "details": exc.errors()
        },
        headers={"X-Request-ID": request_id}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else str(uuid.uuid4())
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )

# Middleware for request logging and request ID
@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next: Callable):
    """Add request ID and log requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url} - "
        f"Headers: {dict(request.headers)}"
    )
    
    # Process request
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        raise
    
    # Calculate process time
    process_time = (time.time() - start_time) * 1000
    process_time = round(process_time, 2)
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(
        f"Response: {request.method} {request.url} - "
        f"Status: {response.status_code} - "
        f"Process Time: {process_time}ms"
    )
    
    return response

# Include API router with security
app.include_router(
    api_router,
    prefix=API_PREFIX,
    dependencies=[Depends(verify_token)],  # Require auth for all API endpoints
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        413: {"model": ErrorResponse, "description": "Payload Too Large"},
        422: {"model": ValidationErrorResponse, "description": "Validation Error"},
        429: {"model": ErrorResponse, "description": "Too Many Requests"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        502: {"model": ErrorResponse, "description": "Bad Gateway"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
        504: {"model": ErrorResponse, "description": "Gateway Timeout"},
    },
    tags=["API v1"]
)

@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    response_model_exclude_none=True,
    responses={
        200: {"description": "Service is healthy"},
        429: {"model": ErrorResponse, "description": "Too Many Requests"},
        500: {"model": ErrorResponse, "description": "Service is unhealthy"},
    },
    tags=["System"],
    summary="Health Check",
    description="""
    Check the health status of the API and its dependencies.
    
    Returns:
        - 200: Service is healthy
        - 500: Service is unhealthy (one or more dependencies are down)
        - 429: Too many requests (rate limited)
    """,
)
@limiter.limit(RATE_LIMIT)
async def health_check(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # Add other dependencies to check (e.g., cache, external services)
) -> Dict[str, Any]:
    """
    Health check endpoint that verifies the status of the API and its dependencies.
    
    This endpoint performs the following checks:
    - Database connectivity
    - External service status (if any)
    - System resources (CPU, memory, disk)
    
    The response includes detailed status information for each component.
    """
    # Initialize response
    health_info = {
        "status": "ok",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": ENVIRONMENT,
        "services": {},
        "system": {},
        "uptime": time.time() - startup_time,
    }
    
    # Check database connection
    db_status = "ok"
    try:
        db.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = f"error: {str(e)}"
        health_info["status"] = "degraded"
    
    health_info["services"]["database"] = db_status
    
    # Add system information (CPU, memory, disk)
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        health_info["system"] = {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            }
        }
        
        # Check if system is under high load
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            health_info["status"] = "degraded"
            
    except ImportError:
        logger.warning("psutil not installed, skipping system metrics")
    
    # Add request ID to response headers
    response_headers = {
        "X-Request-ID": request.state.request_id,
        "X-Response-Time": str(time.time() - request.state.start_time),
    }
    
    # Schedule any background tasks
    background_tasks.add_task(
        log_health_check,
        request_id=request.state.request_id,
        status=health_info["status"],
        response_time=time.time() - request.state.start_time,
    )
    
    # Return appropriate status code based on health status
    if health_info["status"] != "ok":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": "Service is unhealthy",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": health_info,
                "request_id": request.state.request_id,
            },
            headers=response_headers,
        )
    
    return {
        "status": "success",
        "data": health_info,
        "meta": {
            "request_id": request.state.request_id,
            "response_time": time.time() - request.state.start_time,
        },
    }

async def log_health_check(request_id: str, status: str, response_time: float):
    """Log health check results asynchronously"""
    logger.info(
        f"Health check completed - "
        f"Request ID: {request_id} - "
        f"Status: {status} - "
        f"Response Time: {response_time:.2f}s"
    )

@app.get(
    "/",
    response_model=SuccessResponse,
    response_model_exclude_none=True,
    responses={
        200: {"description": "API information"},
    },
    tags=["System"],
    summary="API Information",
    description="""
    Root endpoint that provides information about the API and available endpoints.
    
    This endpoint does not require authentication and provides basic information
    about the API version, available documentation, and main endpoints.
    """,
)
async def root(request: Request) -> Dict[str, Any]:
    """
    Root endpoint with API information and documentation links.
    
    Returns basic information about the API including:
    - Service name and version
    - Available documentation (Swagger UI, ReDoc, OpenAPI spec)
    - Main API endpoints
    - Current environment
    """
    base_url = str(request.base_url).rstrip("/")
    api_url = f"{base_url}{API_PREFIX}"
    
    info = {
        "service": "ForensiQ API",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "documentation": {
            "swagger_ui": f"{base_url}/docs",
            "redoc": f"{base_url}/redoc",
            "openapi_spec": f"{base_url}/openapi.json",
        },
        "endpoints": {
            "health": f"{base_url}/health",
            "api_v1": api_url,
            "api_docs": {
                "swagger": f"{base_url}/docs",
                "redoc": f"{base_url}/redoc",
            },
        },
        "links": {
            "homepage": "https://forensiq.example.com",
            "documentation": "https://docs.forensiq.example.com",
            "support": "mailto:support@forensiq.example.com",
            "status": "https://status.forensiq.example.com",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    return {
        "status": "success",
        "data": info,
        "meta": {
            "request_id": request.state.request_id if hasattr(request.state, 'request_id') else None,
            "response_time": time.time() - request.state.start_time if hasattr(request.state, 'start_time') else None,
        },
    }

# Add application startup time
startup_time = time.time()

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses"""
    start_time = time.time()
    request.state.start_time = start_time
    
    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        # Log unhandled exceptions
        logger.error(
            f"Unhandled exception: {str(e)}",
            exc_info=True,
            extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "path": request.url.path,
                "method": request.method,
            }
        )
        raise
    
    # Calculate process time
    process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Add headers
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    response.headers["X-Request-ID"] = request.state.request_id
    
    # Add Server-Timing header
    response.headers["Server-Timing"] = f"total;dur={process_time:.2f}"
    
    # Log slow requests
    if process_time > 1000:  # Log requests slower than 1 second
        logger.warning(
            f"Slow request: {request.method} {request.url} - {process_time:.2f}ms",
            extra={
                "request_id": request.state.request_id,
                "process_time": f"{process_time:.2f}ms",
                "status_code": response.status_code,
            }
        )
    
    return response

# Add request timeout middleware
@app.middleware("http")
async def timeout_middleware(request: Request, call_next: Callable):
    """Add request timeout"""
    try:
        return await asyncio.wait_for(
            call_next(request),
            timeout=float(os.getenv("REQUEST_TIMEOUT", "30.0")),
        )
    except asyncio.TimeoutError:
        logger.warning(f"Request timeout: {request.method} {request.url}")
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"error": "Request timeout"},
        )

# Add request size limit middleware
@app.middleware("http")
async def check_content_length(request: Request, call_next: Callable):
    """Check content length for file uploads"""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": f"File too large. Maximum size is {MAX_UPLOAD_SIZE} bytes"},
        )
    return await call_next(request)

def get_uvicorn_config() -> dict:
    """Get Uvicorn configuration from environment variables"""
    return {
        "app": "main:app",
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8000")),
        "reload": os.getenv("RELOAD", "false").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "info").lower(),
        "workers": int(os.getenv("WORKERS", "1")),
        "proxy_headers": True,
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", "*"),
        "timeout_keep_alive": int(os.getenv("KEEP_ALIVE_TIMEOUT", "5")),
        "limit_concurrency": int(os.getenv("UVICORN_LIMIT_CONCURRENCY", "1000")),
        "limit_max_requests": int(os.getenv("UVICORN_LIMIT_MAX_REQUESTS", "10000")),
        "timeout_graceful_shutdown": int(os.getenv("UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN", "5")),
        "server_header": False,  # Disable Server header for security
        "date_header": False,    # Let the framework handle the Date header
    }

def configure_uvicorn_logging():
    """Configure Uvicorn logging"""
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }
    
    if IS_PRODUCTION:
        # In production, log to file with rotation
        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": "logs/uvicorn.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        log_config["handlers"]["access_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "access",
            "filename": "logs/access.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        log_config["loggers"]["uvicorn.access"]["handlers"] = ["access", "access_file"]
        log_config["loggers"]["uvicorn"]["handlers"] = ["default", "file"]
    
    return log_config

def main():
    """Main entry point for the application"""
    # Configure logging
    log_config = configure_uvicorn_logging()
    
    # Get Uvicorn config
    config = get_uvicorn_config()
    
    # Print startup banner
    print("""
    ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗███████╗     ██████╗
    ██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝    ██╔═══██╗
    █████╗  ██║   ██║██████╔╝███████╗██╔██╗ ██║█████╗      ██║   ██║
    ██╔══╝  ██║   ██║██╔══██╗╚════██║██║╚██╗██║██╔══╝      ██║   ██║
    ██║     ╚██████╔╝██║  ██║███████║██║ ╚████║███████╗    ╚██████╔╝
    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚══════╝     ╚═════╝ 
    
    Digital Forensics Platform - API Server
    Version: {}
    Environment: {}
    Listening on: http://{}:{}
    
    Press Ctrl+C to stop
    """.format(
        API_VERSION,
        ENVIRONMENT,
        config["host"],
        config["port"]
    ))
    
    # Run the application
    uvicorn.run(
        **config,
        log_config=log_config,
        log_level=LOG_LEVEL.lower(),
        use_colors=not IS_PRODUCTION,
    )

if __name__ == "__main__":
    main()
    title="ForensiQ API",
    description="Core API for ForensiQ digital forensics platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "service": "forensiq-api",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ForensiQ API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "api_v1": "/api/v1"
        },
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )