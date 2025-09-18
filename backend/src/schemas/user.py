""User-related Pydantic models."""
from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, validator

from .base import BaseModel

class UserBase(BaseModel):
    """Base user model with common fields."""
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address"
    )
    full_name: Optional[str] = Field(
        None,
        description="User's full name"
    )
    is_active: Optional[bool] = Field(
        True,
        description="Whether the user account is active"
    )
    is_superuser: bool = Field(
        False,
        description="Whether the user has superuser privileges"
    )

class UserCreate(UserBase):
    """Model for creating a new user."""
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User's password"
    )
    
    @validator("password")
    def validate_password_strength(cls, v: str) -> str:
        ""Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class UserUpdate(UserBase):
    """Model for updating an existing user."""
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="New password (optional)"
    )

class UserInDBBase(UserBase):
    ""Base model for user stored in database."""
    id: str = Field(..., description="Unique identifier for the user")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime = Field(..., description="When the user was last updated")
    last_login: Optional[datetime] = Field(
        None,
        description="When the user last logged in"
    )

    class Config:
        orm_mode = True

class UserInDB(UserInDBBase):
    ""User model with sensitive data for internal use."""
    hashed_password: str = Field(..., description="Hashed password")

class UserResponse(UserInDBBase):
    ""User model for API responses."""
    pass
