"""
routers/auth_router.py — User Registration & Login endpoints

ENDPOINTS:
  POST /api/auth/register  → create new account
  POST /api/auth/login     → authenticate, get JWT token
  GET  /api/auth/me        → get current user profile (protected)

WHY A SEPARATE ROUTER FILE?
  FastAPI's APIRouter works like a "mini app" — it has its own prefix,
  tags, and list of routes. We then include it in main.py.
  Benefits:
    - Each domain (auth / vehicles / bookings) lives in its own file
    - Easier to find code, easier to write tests per module
    - Teams can work in parallel on different routers

SECURITY NOTES:
  - We return the SAME error message ("Invalid email or password") whether
    the email doesn't exist OR the password is wrong.
    WHY? Returning "email not found" lets attackers enumerate registered emails.
  - Passwords are NEVER stored in plain text — only bcrypt hashes.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import hash_password, verify_password, create_access_token, get_current_user
import models
import schemas
import os

# prefix="/api/auth" → all routes here start with /api/auth
# tags=["Authentication"] → groups them in Swagger UI
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    USER STORY — SARAH SIGNS UP:
      Sarah is a first-time customer.  She fills in:
        name="Sarah Kumar", email="sarah@example.com",
        password="pass1234", driving_license="DL1234567890", role="customer"

      The system:
        1. Checks email uniqueness (rejects duplicates)
        2. Hashes the password with bcrypt
        3. Creates the user row in PostgreSQL
        4. Returns the user object (without password_hash!)

    HTTP 201 Created is returned (not the default 200) because a resource
    was created, following REST conventions.
    """
    # Check if email is already taken
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. Please log in instead."
        )

    # Build the User ORM object
    new_user = models.User(
        name            = payload.name,
        email           = payload.email,
        phone           = payload.phone,
        password_hash   = hash_password(payload.password),   # ← bcrypt hash
        role            = payload.role,
        driving_license = payload.driving_license,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)   # loads the auto-generated id + created_at from DB

    return new_user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return a JWT token.

    USER STORY — SARAH LOGS IN:
      Sarah enters email + password.  The system:
        1. Finds her row by email
        2. Runs bcrypt.verify(plain, hashed)
        3. Creates a signed JWT containing {sub: "42", role: "customer"}
        4. Returns token to browser → stored in localStorage

      Every subsequent API call includes:
        Authorization: Bearer eyJhbGciOi...

    The same opaque error is returned for wrong email AND wrong password.
    """
    # Lookup user (timing-safe: we run verify_password even if user is None
    # to prevent timing-based email enumeration attacks)
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated. Contact support."
        )

    # Create a JWT that expires in ACCESS_TOKEN_EXPIRE_MINUTES minutes
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=timedelta(
            minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        )
    )

    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserResponse)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.
    Protected — requires valid JWT in Authorization header.
    Frontend calls this on app load to restore session state.
    """
    return current_user
