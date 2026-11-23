from pathlib import Path

import pytest

from agent_lumos.cli import make_config_file
from agent_lumos.config import AgentConfig, load_env_file


def test_remote_api_requires_tls(config):
    config = AgentConfig(**{**vars(config), "host": "0.0.0.0"})
    with pytest.raises(ValueError, match="TLS"):
        config.validate()


def test_remote_telemetry_requires_https(config):
    config = AgentConfig(**{**vars(config), "telemetry_url": "http://example.com/metrics"})
    with pytest.raises(ValueError, match="HTTPS"):
        config.validate()


def test_local_telemetry_allowed(config):
    config = AgentConfig(**{**vars(config), "telemetry_url": "http://127.0.0.1:8766/v1/report"})
    config.validate()


def test_secure_init_permissions(tmp_path: Path, monkeypatch):
    path = tmp_path / ".env"
    make_config_file(path, "TestPassword!2026")
    assert "TestPassword!2026" not in path.read_text()
    assert "LUMOS_JWT_SECRET=" in path.read_text()
    if __import__("os").name == "posix":
        assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        make_config_file(path, "TestPassword!2026")
    for key in ("LUMOS_JWT_SECRET", "LUMOS_ADMIN_PASSWORD_HASH", "LUMOS_FERNET_KEY"):
        monkeypatch.delenv(key, raising=False)
    load_env_file(path)
    cfg = AgentConfig.from_env()
    assert cfg.port == 8765
