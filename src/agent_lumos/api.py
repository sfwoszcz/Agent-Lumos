"""Async HTTP API: JWT authentication and safe, read-only endpoints."""

from __future__ import annotations

import asyncio
import logging

from aiohttp import web
import jwt

from . import __version__
from .config import AgentConfig
from .monitor import SystemMonitor
from .security import JWTAuthenticator, LoginLimiter
from .stm32 import STM32Registry, collect_serial
from .telemetry import TelemetryReporter

LOGGER = logging.getLogger(__name__)


class AgentAPI:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.monitor = SystemMonitor(config.agent_id)
        self.auth = JWTAuthenticator(config.jwt_secret, config.username, config.admin_password_hash)
        self.limiter = LoginLimiter()
        self.reporter = TelemetryReporter(config, self.monitor)
        self.stm32 = STM32Registry()
        self._stm32_task: asyncio.Task | None = None

    def _require_token(self, request: web.Request, scope: str) -> None:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 4096:
            raise web.HTTPUnauthorized(text="Bearer token required")
        try:
            self.auth.verify_token(token, scope)
        except jwt.InvalidTokenError:
            LOGGER.warning("Rejected invalid bearer token from %s", request.remote)
            raise web.HTTPUnauthorized(text="Invalid or expired bearer token") from None

    async def health(self, request: web.Request) -> web.Response:
        return web.json_response({"service": "agent-lumos", "status": "ok", "version": __version__})

    async def login(self, request: web.Request) -> web.Response:
        if not self.limiter.allow(request.remote or "unknown"):
            return web.json_response({"error": "Too many login attempts"}, status=429)
        try:
            data = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "JSON body required"}, status=400)
        if (not isinstance(data, dict)
                or not isinstance(data.get("username"), str)
                or not isinstance(data.get("password"), str)
                or len(data["username"]) > 100 or len(data["password"]) > 1024):
            return web.json_response({"error": "username and password must be strings"}, status=400)
        token = self.auth.login(data["username"], data["password"])
        if not token:
            LOGGER.warning("Invalid login attempt from %s", request.remote)
            return web.json_response({"error": "Invalid credentials"}, status=401)
        LOGGER.info("Administrator login succeeded from %s", request.remote)
        return web.json_response({"access_token": token, "token_type": "Bearer", "expires_in": 900})

    async def metrics(self, request: web.Request) -> web.Response:
        self._require_token(request, "metrics:read")
        return web.json_response(self.monitor.collect())

    async def diagnostics(self, request: web.Request) -> web.Response:
        self._require_token(request, "diagnostics:read")
        try:
            data = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "JSON body required"}, status=400)
        if not isinstance(data, dict) or not isinstance(data.get("action"), str):
            return web.json_response({"error": "Expected an action string"}, status=400)
        try:
            result = self.monitor.diagnostic(data["action"])
        except ValueError as exc:
            LOGGER.warning("Rejected unknown diagnostic from %s", request.remote)
            return web.json_response({"error": str(exc)}, status=400)
        LOGGER.info("Diagnostic '%s' requested from %s", data["action"], request.remote)
        return web.json_response({"action": data["action"], "result": result})

    async def stm32_devices(self, request: web.Request) -> web.Response:
        self._require_token(request, "stm32:read")
        devices = self.stm32.snapshot()
        return web.json_response({"devices": devices, "count": len(devices)})

    async def _startup(self, app: web.Application) -> None:
        self.reporter.start()
        if self.config.stm32_port:
            try:
                import serial  # noqa: F401; optional dependency, validated at startup
            except ImportError as exc:
                raise RuntimeError("For STM32 integration install: pip install 'agent-lumos[stm32]'") from exc
            self._stm32_task = asyncio.create_task(
                collect_serial(self.config.stm32_port, self.config.stm32_baud, self.stm32),
                name="stm32-uart-collector",
            )

    async def _cleanup(self, app: web.Application) -> None:
        if self._stm32_task:
            self._stm32_task.cancel()
            try:
                await self._stm32_task
            except asyncio.CancelledError:
                pass
        await self.reporter.stop()

    def create_app(self) -> web.Application:
        app = web.Application(client_max_size=2048)
        app.add_routes([
            web.get("/health", self.health),
            web.post("/v1/login", self.login),
            web.get("/v1/metrics", self.metrics),
            web.post("/v1/diagnostics", self.diagnostics),
            web.get("/v1/stm32/devices", self.stm32_devices),
        ])
        app.on_startup.append(self._startup)
        app.on_cleanup.append(self._cleanup)
        return app
