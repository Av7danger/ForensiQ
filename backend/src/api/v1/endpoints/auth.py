""Authentication endpoints."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.security import create_access_token, authenticate_user, get_password_hash
from ...db.session import get_db
from ...models.user import User
from ...schemas.token import Token, TokenPayload
from ...schemas.user import UserCreate, UserInDB, UserResponse
from ...services.user_service import create_new_user, get_user_by_email

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
    access_token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserResponse)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    """
    # Check if user already exists
    user = get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    
    # Create new user
    user = create_new_user(db=db, user_in=user_in)
    return user

@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Test access token.
    """
    return current_user
