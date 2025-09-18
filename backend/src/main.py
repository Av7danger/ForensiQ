""
ForensiQ API - Digital Forensics Platform
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import v1 as api_v1
from .api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .config import configure_logging, get_settings
from .db.session import SessionLocal, engine
from .models.base import Base
from .schemas.base import BaseResponse
from .schemas.error import ErrorResponse
from .schemas.health import HealthCheckResponse, HealthStatus
from .utils.logging import get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    ""Application startup and shutdown events."""
    # Startup
    logger.info("Starting ForensiQ API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ForensiQ API...")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ForensiQ API - Digital Forensics Platform",
    version=settings.VERSION,
    docs_url=None,  # Disable default Swagger UI
    redoc_url=None,  # Disable default ReDoc
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)

# Add exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# API Router
app.include_router(api_v1.router, prefix=settings.API_V1_STR)

# Custom OpenAPI schema
def custom_openapi():
    ""Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="ForensiQ API - Digital Forensics Platform",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security to all endpoints
    for path in openapi_schema["paths"].values():
        for method in path.values():
            # Skip if already has security
            if "security" in method:
                continue
            # Skip public endpoints
            if any(public_path in method.get("tags", []) for public_path in ["public"]):
                continue
            # Add security
            method["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom docs endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    ""Custom Swagger UI with dark theme."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.PROJECT_NAME} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "none",
            "filter": True,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "syntaxHighlight.theme": "monokai",
            "theme": {
                "extend": {
                    "colors": {
                        "primary": {
                            "50": "#f0fdf4",
                            "100": "#dcfce7",
                            "200": "#bbf7d0",
                            "300": "#86efac",
                            "400": "#4ade80",
                            "500": "#22c55e",
                            "600": "#16a34a",
                            "700": "#15803d",
                            "800": "#166534",
                            "900": "#14532d",
                        }
                    }
                }
            }
        },
    )

# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
    response_description="Health status information",
)
async def health_check() -> HealthCheckResponse:
    ""Health check endpoint."""
    # Check database connection
    db_status = HealthStatus.HEALTHY
    db_error = None
    
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        db_status = HealthStatus.UNHEALTHY
        db_error = str(e)
        logger.error(f"Database health check failed: {e}")
    
    # Check overall status
    status = HealthStatus.HEALTHY
    if db_status == HealthStatus.UNHEALTHY:
        status = HealthStatus.DEGRADED
    
    return HealthCheckResponse(
        status=status,
        version=settings.VERSION,
        checks={
            "database": {
                "status": db_status,
                "error": db_error,
            },
        },
    )

# Root endpoint
@app.get(
    "/",
    response_model=BaseResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    tags=["Root"],
    summary="Root Endpoint",
    description="Root endpoint that provides API information and documentation links",
    response_description="API information",
)
async def root() -> BaseResponse[Dict[str, Any]]:
    ""Root endpoint with API information."""
    return BaseResponse[Dict[str, Any]](
        data={
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
            },
            "endpoints": {
                "health": "/health",
                "api_v1": settings.API_V1_STR,
            },
        },
        message=f"Welcome to {settings.PROJECT_NAME} API v{settings.VERSION}",
    )
