""API v1 router."""
from fastapi import APIRouter

from .endpoints import auth, cases, evidence, users

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence"])
