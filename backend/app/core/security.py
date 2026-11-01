import base64
import hashlib
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from cryptography.fernet import Fernet

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Exception:
        return False


def encryption_key(value: str, fallback_secret: str) -> bytes:
    if value:
        return value.encode()
    # Development fallback; production must set TOKEN_ENCRYPTION_KEY.
    digest = hashlib.sha256(fallback_secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt(value: str, key: bytes) -> str:
    return Fernet(key).encrypt(value.encode()).decode()


def decrypt(value: str, key: bytes) -> str:
    return Fernet(key).decrypt(value.encode()).decode()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive timestamps to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def lock_until(hours: int = 3) -> datetime:
    return utcnow() + timedelta(hours=hours)
