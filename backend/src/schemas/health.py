""Health check related schemas."""
from enum import Enum
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

from .base import BaseResponse

class HealthStatus(str, Enum):
    ""Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthCheck(BaseModel):
    ""Health check response model."""
    status: HealthStatus = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    checks: Dict[str, Dict[str, Optional[str]]] = Field(
        ...,
        description="Health check results for different components"
    )

class HealthCheckResponse(BaseResponse[HealthCheck]):
    ""Health check response wrapper."""
    data: HealthCheck = Field(..., description="Health check results")
