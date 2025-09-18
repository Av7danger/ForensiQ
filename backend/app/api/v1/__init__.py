"""
API v1 router configuration.
"""
from fastapi import APIRouter
from .endpoints import cases

api_router = APIRouter()
api_router.include_router(cases.router, prefix="/api/v1", tags=["cases"])
