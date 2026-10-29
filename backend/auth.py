import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

_JWT_SECRET_PLACEHOLDERS = {
    "change_this_secret",
    "change-this-development-secret",
}


def validate_jwt_secret(secret: str | None) -> str:
    if secret is None or not secret.strip():
        raise RuntimeError("JWT_SECRET_KEY is required and must not be empty.")

    normalized_secret = secret.strip().casefold()
    if (
        normalized_secret in _JWT_SECRET_PLACEHOLDERS
        or normalized_secret.startswith(("change_this_", "replace_with_"))
    ):
        raise RuntimeError("JWT_SECRET_KEY must be a generated secret, not an example placeholder.")

    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes long.")

    return secret


JWT_SECRET_KEY = validate_jwt_secret(os.getenv("JWT_SECRET_KEY"))

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
IDLE_SESSION_TIMEOUT_SECONDS = 300


def utcnow_naive() -> datetime:
    """Return UTC in the naive format used by MySQL DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return hashed.decode("utf-8")


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_access_token(
    user_id: int,
    username: str,
    role: str,
    session_id: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
