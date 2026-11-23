import pytest

from agent_lumos.config import AgentConfig
from agent_lumos.security import PasswordHasher


@pytest.fixture(scope="session")
def password_hash():
    return PasswordHasher.hash_password("TestPassword!2026")


@pytest.fixture
def config(password_hash):
    return AgentConfig(jwt_secret="v" * 48,
                       admin_password_hash=password_hash,
                       telemetry_token="t" * 32)
