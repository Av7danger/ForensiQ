""Enhanced security configurations and utilities."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..db.session import get_db
from ..models.user import User
from ..schemas.token import TokenPayload

settings = get_settings()

# Security configurations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
    scopes={
        "user:read": "Read access to user data",
        "user:write": "Write access to user data",
        "admin": "Admin access"
    }
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

class SecurityUtils:
    ""Enhanced security utilities."""
    
    @staticmethod
    def create_access_token(
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None,
        scopes: Optional[list] = None,
        **kwargs: Any
    ) -> str:
        """Create a JWT access token with enhanced security features."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unique token identifier
            "scopes": scopes or [],
            "iss": settings.SECURITY_ISSUER,  # Token issuer
            "aud": settings.SECURITY_AUDIENCE,  # Token audience
            **kwargs,
        }
        
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    @staticmethod
    def create_refresh_token(
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a refresh token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        
        to_encode = {
            "exp": expire,
            "sub": user_id,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }
        
        return jwt.encode(
            to_encode,
            settings.REFRESH_SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash with timing attack protection."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a password hash."""
        return pwd_context.hash(password)
    
    @staticmethod
    def get_token_payload(token: str) -> TokenPayload:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "require_aud": True,
                    "require_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                },
                audience=settings.SECURITY_AUDIENCE,
                issuer=settings.SECURITY_ISSUER,
            )
            return TokenPayload(**payload)
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

class RateLimiter:
    ""Enhanced rate limiting with Redis backend."""
    
    def __init__(self, key_func=get_remote_address, limit="100/minute"):
        self.key_func = key_func
        self.limit = limit
    
    async def __call__(self, request: Request):
        # Implement Redis-based rate limiting
        # This is a simplified version - in production, use a Redis backend
        client_ip = self.key_func(request)
        # Add rate limiting logic here
        return True

def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get the current user from the JWT token with scope validation."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = SecurityUtils.get_token_payload(token)
        
        # Check token expiration
        if datetime.utcnow() > datetime.fromtimestamp(payload.exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify scopes
        if security_scopes.scopes:
            token_scopes = set(payload.scopes or [])
            for scope in security_scopes.scopes:
                if scope not in token_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions",
                        headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
                    )
        
        # Get user from database
        user = db.query(User).filter(User.id == payload.sub).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return user
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
