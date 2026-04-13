"""
auth.py — JWT Authentication & Role-Based Access Control

WHAT IS JWT (JSON Web Token)?
  A JWT is a compact, signed string that proves who the user is.
  Structure:  base64(header) . base64(payload) . HMAC-signature
    - header:    algorithm used (HS256)
    - payload:   user_id, role, expiry timestamp
    - signature: HMAC of header+payload with our SECRET_KEY

  The server NEVER stores the token.  When a request arrives, we:
    1. Decode the token with our secret key (tamper detection is automatic)
    2. Check the 'exp' claim to reject expired tokens
    3. Look up the user_id from the payload in the DB

WHY NOT SESSIONS?
  Session-based auth stores session state on the server (memory or DB).
  JWT is stateless — the token itself carries everything we need.
  This scales to multiple backend servers without shared session storage.

FLOW:
  Client              Server
  ──────────────────────────────────────────────────
  POST /login  ──▶   verify password
               ◀──   JWT token (30-min expiry)
  GET /vehicles ──▶  verify token → extract user_id/role
  (Authorization: Bearer <token>)

PASSWORD HASHING — WHY BCRYPT?
  MD5 / SHA-256 are fast hash functions → attackers can compute billions
  of guesses per second (rainbow table / brute force).
  bcrypt is SLOW BY DESIGN (cost factor). Even modern GPUs need days
  to crack a bcrypt hash. It also auto-generates a random salt so
  identical passwords produce different hashes.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
#  Config (read from .env)
# ──────────────────────────────────────────────────────────────
SECRET_KEY                 = os.getenv("SECRET_KEY",  "change-me-in-production")
ALGORITHM                  = os.getenv("ALGORITHM",   "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ──────────────────────────────────────────────────────────────
#  Password hashing context
#  schemes=["bcrypt"] — use bcrypt as the primary algorithm
#  deprecated="auto"  — if a stored hash uses an old algorithm,
#                        Passlib will transparently rehash it on next login
# ──────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer tells FastAPI:
#   "Look for the token in the Authorization: Bearer <token> header."
#   tokenUrl points to the login endpoint (used by Swagger UI's Authorize button).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ──────────────────────────────────────────────────────────────
#  Password utilities
# ──────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash a plain-text password with bcrypt.

    Example:
      "mysecret" → "$2b$12$EixZaYVK1fsbw1ZfbX3OXe..."  (60-char bcrypt hash)

    The hash embeds:
      - algorithm version ($2b$)
      - cost factor      ($12$) — 2^12 = 4096 iterations
      - random 22-char salt
      - 31-char digest
    """
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain password against its bcrypt hash.
    Passlib extracts the salt from the hash, re-computes, and compares.
    Returns True only if they match.
    """
    return pwd_context.verify(plain, hashed)


# ──────────────────────────────────────────────────────────────
#  Token creation
# ──────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT token.

    Args:
        data          : dict to embed in payload (typically {"sub": str(user_id), "role": role})
        expires_delta : how long until the token is invalid

    Returns:
        A compact JWT string like "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."

    'sub' (subject) is the standard JWT claim for the principal identity.
    We store user_id as string in 'sub', role as a separate claim.
    """
    to_encode = data.copy()

    # Set expiry time
    expire = datetime.utcnow() + (
        expires_delta if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    # jwt.encode signs the payload with our secret key
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ──────────────────────────────────────────────────────────────
#  Current-user dependency  (used by protected endpoints)
# ──────────────────────────────────────────────────────────────

def get_current_user(
    token: str          = Depends(oauth2_scheme),
    db:    Session      = Depends(get_db)
) -> models.User:
    """
    FastAPI dependency — decodes the JWT and returns the authenticated User.

    Every protected route declares:
        current_user: models.User = Depends(get_current_user)

    FastAPI automatically:
      1. Extracts token from Authorization header
      2. Calls this function
      3. Passes the returned User object to the endpoint

    Raises HTTP 401 if token is missing, expired, or tampered.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials — please log in again",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and verify signature + expiry in one call
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Look up user in DB (token could be valid but user deactivated since)
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ──────────────────────────────────────────────────────────────
#  Role-Based Access Control (RBAC) factory
# ──────────────────────────────────────────────────────────────

def require_role(*roles: str):
    """
    Dependency factory for role-gated endpoints.

    Usage:
        # Only admins can access this endpoint
        @router.post("/vehicles")
        def add_vehicle(user = Depends(require_role("admin"))):
            ...

        # Both admins and fleet managers can access
        @router.patch("/vehicles/{id}/status")
        def update_status(user = Depends(require_role("admin", "fleet_manager"))):
            ...

    WHY factory pattern?
      Depends() expects a callable. By wrapping the checker in an outer
      function we can parameterise it (pass arbitrary role names)
      while still returning a regular dependency function.
    """
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}"
            )
        return current_user
    return role_checker
