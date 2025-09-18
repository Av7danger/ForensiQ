""User service for handling user-related operations."""
from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from ..core.security import get_password_hash, verify_password
from ..db.models.user import User
from ..schemas.user import UserCreate, UserUpdate

def get_user(db: Session, user_id: str) -> Optional[User]:
    ""Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    ""Get a user by email."""
    return db.query(User).filter(User.email == email).first()

def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100
) -> list[User]:
    ""Get a list of users with pagination."""
    return db.query(User).offset(skip).limit(limit).all()

def create_new_user(
    db: Session, 
    user_in: UserCreate,
) -> User:
    ""Create a new user."""
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        is_superuser=user_in.is_superuser,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(
    db: Session, 
    db_user: User, 
    user_in: Union[UserUpdate, Dict[str, Any]]
) -> User:
    ""Update a user."""
    if isinstance(user_in, dict):
        update_data = user_in
    else:
        update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: str) -> User:
    ""Delete a user."""
    user = get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    db.delete(user)
    db.commit()
    return user

def authenticate(
    db: Session, 
    email: str, 
    password: str
) -> Optional[User]:
    ""Authenticate a user."""
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
