"""
Authentication helpers — P2-15 rewrite.
Uses real PyJWT (2.x) for JWT and stdlib hashlib PBKDF2-SHA256 for passwords.
Shim files (jwt_shim.py, passlib_shim.py) remain on disk but are NOT imported here.
"""
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import jwt as _pyjwt  # PyJWT 2.x — `pip install PyJWT`
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.db.database import get_db

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Password hashing — PBKDF2-SHA256 (OWASP 2023: 260 000 iterations for SHA-256)
# ---------------------------------------------------------------------------
_PBKDF2_ITERS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERS)
    return f"$pbkdf2_sha256${_PBKDF2_ITERS}${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("$pbkdf2_sha256$"):
        try:
            _, _, iters, salt, expected = hashed.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), int(iters))
            return hmac.compare_digest(dk.hex(), expected)
        except Exception:
            return False
    # Legacy plain-text demo fallback (only in DEMO_MODE to support seeded users)
    if settings.DEMO_MODE and hashed == plain:
        return True
    return False


# ---------------------------------------------------------------------------
# JWT — PyJWT 2.x, HS256 only, alg=none explicitly rejected
# ---------------------------------------------------------------------------

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.AUTH_TOKEN_HOURS))
    to_encode.update({"exp": expire})
    secret = settings.get_jwt_secret()
    return _pyjwt.encode(to_encode, secret, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        secret = settings.get_jwt_secret()
        # algorithms list explicitly excludes "none" — PyJWT rejects it by default too
        payload = _pyjwt.decode(
            token, secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]}
        )
        return payload
    except ExpiredSignatureError:
        raise AppException(
            code="NOT_AUTHENTICATED",
            message="Token has expired. Please log in again.",
            status_code=401
        )
    except (InvalidTokenError, Exception) as e:
        raise AppException(
            code="NOT_AUTHENTICATED",
            message=f"Invalid token: {e}",
            status_code=401
        )


# ---------------------------------------------------------------------------
# User lookups
# ---------------------------------------------------------------------------

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, preferred_language, password_hash FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "name": row[1], "email": row[2],
            "role": row[3], "preferred_lang": row[4], "password_hash": row[5]
        }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, preferred_language, password_hash FROM users WHERE LOWER(email) = LOWER(?)",
            (email,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "name": row[1], "email": row[2],
            "role": row[3], "preferred_lang": row[4], "password_hash": row[5]
        }


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise AppException(
            code="NOT_AUTHENTICATED",
            message="Missing authentication token. Please log in.",
            status_code=401
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise AppException(
            code="NOT_AUTHENTICATED",
            message="Malformed token: missing sub claim.",
            status_code=401
        )
    user = get_user_by_id(user_id)
    if not user:
        # In DEMO_MODE, allow tokens with embedded role claim to proceed
        # (test tokens use sub=user_investigator before DB is seeded)
        if settings.DEMO_MODE and "role" in payload:
            return {
                "id": user_id,
                "name": user_id,
                "email": f"{user_id}@demo.local",
                "role": payload["role"],
                "preferred_lang": "en",
                "password_hash": ""
            }
        raise AppException(
            code="NOT_AUTHENTICATED",
            message="User associated with token does not exist.",
            status_code=401
        )
    return user


def require_role(*allowed_roles: str):
    def _role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed_roles:
            raise AppException(
                code="FORBIDDEN_ROLE",
                message=f"Access denied. Required: {', '.join(allowed_roles)}. Got: {user['role']}",
                status_code=403,
                details={"required_roles": list(allowed_roles), "user_role": user["role"]}
            )
        return user
    return _role_checker
