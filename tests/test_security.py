import pytest
import jwt

from agent_lumos.security import JWTAuthenticator, LoginLimiter, PasswordHasher


def test_password_hash_and_verify():
    digest = PasswordHasher.hash_password("example-test-password-2026")
    assert "example-test-password-2026" not in digest
    assert PasswordHasher.verify("example-test-password-2026", digest)
    assert not PasswordHasher.verify("wrong-password", digest)
    assert not PasswordHasher.verify("foo", "not-a-valid-hash")


def test_short_password_rejected():
    with pytest.raises(ValueError):
        PasswordHasher.hash_password("short")


def test_jwt_valid_and_invalid(config):
    auth = JWTAuthenticator(config.jwt_secret, "admin", config.admin_password_hash)
    assert auth.login("admin", "wrong") is None
    assert auth.login("somebody", "TestPassword!2026") is None
    token = auth.login("admin", "TestPassword!2026")
    assert auth.verify_token(token, "metrics:read")["sub"] == "admin"
    with pytest.raises(jwt.InvalidTokenError):
        auth.verify_token(token, "admin:write")
    with pytest.raises(jwt.InvalidTokenError):
        JWTAuthenticator("x" * 48, "admin", config.admin_password_hash).verify_token(token, "metrics:read")


def test_rate_limit():
    limit = LoginLimiter(capacity=2)
    assert limit.allow("127.0.0.1")
    assert limit.allow("127.0.0.1")
    assert not limit.allow("127.0.0.1")
    assert limit.allow("127.0.0.2")
