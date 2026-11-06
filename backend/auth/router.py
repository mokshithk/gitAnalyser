from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User
from backend.auth.schemas import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    SystemLimitsResponse,
)
from backend.auth.security import hash_password, verify_password, create_access_token
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # First user can be made admin if role is passed as admin, otherwise standard user
    role = "admin" if user_in.role == "admin" else "user"
    user = User(
        email=user_in.email.lower(),
        password_hash=hash_password(user_in.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/limits", response_model=SystemLimitsResponse)
def get_system_limits():
    return SystemLimitsResponse(
        max_repo_size_mb=settings.MAX_REPO_SIZE_MB,
        max_zip_size_mb=settings.MAX_ZIP_SIZE_MB,
        clone_timeout_seconds=settings.CLONE_TIMEOUT_SECONDS,
        retention_days=settings.RETENTION_DAYS,
        scans_per_user_per_hour=settings.SCANS_PER_USER_PER_HOUR,
    )
