""Token-related Pydantic models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class Token(BaseModel):
    """JWT token response model."""
    access_token: str = Field(
        ...,
        description="JWT access token for authentication"
    )
    token_type: str = Field(
        "bearer",
        description="Type of the token (always 'bearer')"
    )
    expires_in: Optional[int] = Field(
        None,
        description="Number of seconds until the token expires"
    )

class TokenPayload(BaseModel):
    ""JWT token payload model."""
    sub: Optional[str] = Field(
        None,
        description="Subject (user ID)"
    )
    exp: Optional[datetime] = Field(
        None,
        description="Expiration time"
    )
    iat: Optional[datetime] = Field(
        None,
        description="Issued at time"
    )
    jti: Optional[str] = Field(
        None,
        description="JWT ID"
    )
    
    class Config:
        extra = "allow"  # Allow extra fields in the JWT payload
