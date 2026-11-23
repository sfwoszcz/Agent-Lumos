"""Local-only telemetry receiver for the README demonstration, not a production server."""

from __future__ import annotations

import hmac
import json
import logging

from aiohttp import web
from cryptography.fernet import Fernet, InvalidToken

from .config import AgentConfig

LOGGER = logging.getLogger(__name__)


class DemoReceiver:
    def __init__(self, config: AgentConfig) -> None:
        if not config.telemetry_token:
            raise ValueError("The demo receiver requires LUMOS_TELEMETRY_TOKEN")
        self.token = config.telemetry_token
        self.cipher = Fernet(config.fernet_key.encode()) if config.fernet_key else None

    async def receive(self, request: web.Request) -> web.Response:
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + self.token):
            return web.json_response({"error": "Unauthorized"}, status=401)
        try:
            payload = await request.json()
            if payload.get("format") == "fernet-v1" and self.cipher:
                data = json.loads(self.cipher.decrypt(payload["ciphertext"].encode("ascii")))
            elif payload.get("format") == "json-v1" and not self.cipher:
                data = payload["data"]
            else:
                return web.json_response({"error": "Unexpected payload format"}, status=400)
            if not isinstance(data, dict) or not all(k in data for k in ("agent_id", "cpu_percent", "memory_percent")):
                return web.json_response({"error": "Invalid metrics"}, status=400)
        except (ValueError, TypeError, KeyError, InvalidToken):
            return web.json_response({"error": "Invalid or undecryptable payload"}, status=400)
        LOGGER.info("Received %s telemetry: cpu=%s%% memory=%s%%", data["agent_id"],
                    data["cpu_percent"], data["memory_percent"])
        return web.json_response({"accepted": True, "agent_id": data["agent_id"]})

    def create_app(self) -> web.Application:
        app = web.Application(client_max_size=8192)
        app.router.add_post("/v1/report", self.receive)
        return app
