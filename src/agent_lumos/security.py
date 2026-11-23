"""Password hashing, short-lived JWT tokens, and login throttling."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import logging
import secrets
import time

import jwt

LOGGER = logging.getLogger(__name__)
ITERATIONS = 600_000
ISSUER = "agent-lumos"
AUDIENCE = "agent-lumos-api"


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class PasswordHasher:
    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 12:
            raise ValueError("Choose an administrator password of at least 12 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
        return f"pbkdf2_sha256${ITERATIONS}${_encode(salt)}${_encode(digest)}"

    @staticmethod
    def verify(password: str, stored_hash: str) -> bool:
        try:
            algorithm, count, salt, expected = stored_hash.split("$")
            count_int = int(count)
            if algorithm != "pbkdf2_sha256" or not 200_000 <= count_int <= 2_000_000:
                return False
            calculated = hashlib.pbkdf2_hmac("sha256", password.encode(), _decode(salt), count_int)
            return hmac.compare_digest(calculated, _decode(expected))
        except (ValueError, TypeError, OverflowError):
            return False


class JWTAuthenticator:
    def __init__(self, secret: str, username: str, password_hash: str) -> None:
        self.secret = secret
        self.username = username
        self.password_hash = password_hash

    def login(self, username: str, password: str) -> str | None:
        # Evaluate password verification even for an unknown username.
        matches_name = hmac.compare_digest(username.encode(), self.username.encode())
        matches_password = PasswordHasher.verify(password, self.password_hash)
        if not (matches_name and matches_password):
            return None
        now = datetime.now(timezone.utc)
        claims = {
            "iss": ISSUER, "aud": AUDIENCE, "sub": self.username,
            "iat": now, "nbf": now, "exp": now + timedelta(minutes=15),
            "jti": secrets.token_urlsafe(16), "scope": ["metrics:read", "diagnostics:read", "stm32:read"],
        }
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def verify_token(self, token: str, required_scope: str) -> dict:
        claims = jwt.decode(
            token, self.secret, algorithms=["HS256"],
            audience=AUDIENCE, issuer=ISSUER,
            options={"require": ["exp", "iat", "nbf", "sub", "iss", "aud", "jti"]},
            leeway=5,
        )
        if claims.get("sub") != self.username or required_scope not in claims.get("scope", []):
            raise jwt.InvalidTokenError("Invalid scope or subject")
        return claims


class LoginLimiter:
    """Simple in-memory per-IP rate limit; use a shared gateway for multi-node systems."""

    def __init__(self, capacity: int = 5, window_seconds: int = 60) -> None:
        self.capacity = capacity
        self.window_seconds = window_seconds
        self.events: dict[str, deque[float]] = {}

    def allow(self, address: str) -> bool:
        now = time.monotonic()
        if len(self.events) > 10_000:
            self.events = {ip: entries for ip, entries in self.events.items()
                           if entries and entries[-1] > now - self.window_seconds}
        timestamps = self.events.setdefault(address, deque())
        while timestamps and timestamps[0] <= now - self.window_seconds:
            timestamps.popleft()
        if len(timestamps) >= self.capacity:
            LOGGER.warning("Login rate limit exceeded from %s", address)
            return False
        timestamps.append(now)
        return True
