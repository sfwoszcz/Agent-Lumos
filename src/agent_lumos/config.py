"""Configuration with secure defaults and fail-closed validation."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse


def is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def load_env_file(path: Path) -> None:
    """Read a simple KEY=VALUE config file; pre-existing env vars take precedence."""
    if not path.is_file():
        raise ValueError(f"Config file not found: {path}. Run 'agent-lumos init' first.")
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError(f"Config file {path} is accessible to other users; run chmod 600 {path}")
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.startswith("LUMOS_") or not key.replace("_", "").isalnum():
            raise ValueError(f"Invalid config entry on line {line_number}")
        os.environ.setdefault(key, value.strip())


@dataclass(frozen=True)
class AgentConfig:
    jwt_secret: str
    admin_password_hash: str
    username: str = "admin"
    host: str = "127.0.0.1"
    port: int = 8765
    agent_id: str = "lumos-local"
    interval_seconds: int = 15
    telemetry_url: str | None = None
    telemetry_token: str | None = None
    fernet_key: str | None = None
    tls_cert: Path | None = None
    tls_key: Path | None = None
    log_file: Path = Path("agent_lumos.log")
    stm32_port: str | None = None
    stm32_baud: int = 115200

    @classmethod
    def from_env(cls) -> "AgentConfig":
        def value(name: str) -> str | None:
            return os.getenv(name) or None

        try:
            port = int(os.getenv("LUMOS_PORT", "8765"))
            interval = int(os.getenv("LUMOS_SEND_INTERVAL", "15"))
            stm32_baud = int(os.getenv("LUMOS_STM32_BAUD", "115200"))
        except ValueError as exc:
            raise ValueError("LUMOS_PORT, LUMOS_SEND_INTERVAL and LUMOS_STM32_BAUD must be integers") from exc
        cfg = cls(
            jwt_secret=os.getenv("LUMOS_JWT_SECRET", ""),
            admin_password_hash=os.getenv("LUMOS_ADMIN_PASSWORD_HASH", ""),
            username=os.getenv("LUMOS_USERNAME", "admin"),
            host=os.getenv("LUMOS_HOST", "127.0.0.1"),
            port=port,
            agent_id=os.getenv("LUMOS_AGENT_ID", "lumos-local"),
            interval_seconds=interval,
            telemetry_url=value("LUMOS_TELEMETRY_URL"),
            telemetry_token=value("LUMOS_TELEMETRY_TOKEN"),
            fernet_key=value("LUMOS_FERNET_KEY"),
            tls_cert=Path(value("LUMOS_TLS_CERT")) if value("LUMOS_TLS_CERT") else None,
            tls_key=Path(value("LUMOS_TLS_KEY")) if value("LUMOS_TLS_KEY") else None,
            log_file=Path(os.getenv("LUMOS_LOG_FILE", "agent_lumos.log")),
            stm32_port=value("LUMOS_STM32_PORT"),
            stm32_baud=stm32_baud,
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise ValueError("Set a unique LUMOS_JWT_SECRET of at least 32 bytes")
        if not self.admin_password_hash.startswith("pbkdf2_sha256$"):
            raise ValueError("LUMOS_ADMIN_PASSWORD_HASH is missing or invalid; run 'agent-lumos init'")
        if not self.username or len(self.username) > 100:
            raise ValueError("Invalid LUMOS_USERNAME")
        if not 1 <= self.port <= 65535:
            raise ValueError("LUMOS_PORT must be between 1 and 65535")
        if not 2 <= self.interval_seconds <= 3600:
            raise ValueError("LUMOS_SEND_INTERVAL must be between 2 and 3600 seconds")
        if not is_loopback(self.host) and not (self.tls_cert and self.tls_key):
            raise ValueError("Listening beyond localhost requires TLS cert/key; prefer a VPN or mTLS")
        if bool(self.tls_cert) != bool(self.tls_key):
            raise ValueError("Provide both LUMOS_TLS_CERT and LUMOS_TLS_KEY")
        if self.tls_cert and not (self.tls_cert.is_file() and self.tls_key.is_file()):
            raise ValueError("TLS certificate/key not found")
        if self.telemetry_url:
            parsed = urlparse(self.telemetry_url)
            if not parsed.netloc or parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
                raise ValueError("LUMOS_TELEMETRY_URL must be an http(s) URL without embedded credentials")
            if parsed.scheme != "https" and not is_loopback(parsed.hostname or ""):
                raise ValueError("Remote telemetry must use HTTPS; plain HTTP is localhost-only")
            if not self.telemetry_token or len(self.telemetry_token) < 24:
                raise ValueError("Telemetry URL requires LUMOS_TELEMETRY_TOKEN (24+ characters)")
        if not 1200 <= self.stm32_baud <= 1000000:
            raise ValueError("LUMOS_STM32_BAUD must be 1200..1000000")
        if self.stm32_port and (len(self.stm32_port) > 255 or any(ord(ch) < 32 for ch in self.stm32_port)):
            raise ValueError("Invalid LUMOS_STM32_PORT")
        if self.fernet_key:
            from cryptography.fernet import Fernet
            try:
                Fernet(self.fernet_key.encode("ascii"))
            except (ValueError, TypeError) as exc:
                raise ValueError("LUMOS_FERNET_KEY must be a valid Fernet key") from exc
