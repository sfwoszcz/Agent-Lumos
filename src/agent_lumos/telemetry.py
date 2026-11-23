"""Optional HTTPS outbound telemetry; optional Fernet end-to-end envelope."""

from __future__ import annotations

import asyncio
import json
import logging

import aiohttp
from cryptography.fernet import Fernet

from .config import AgentConfig
from .monitor import SystemMonitor

LOGGER = logging.getLogger(__name__)


class TelemetryReporter:
    def __init__(self, config: AgentConfig, monitor: SystemMonitor) -> None:
        self.config = config
        self.monitor = monitor
        self.cipher = Fernet(config.fernet_key.encode()) if config.fernet_key else None
        self._task: asyncio.Task | None = None

    def make_payload(self) -> dict:
        measurements = self.monitor.collect()
        if self.cipher:
            encoded = json.dumps(measurements, separators=(",", ":")).encode("utf-8")
            return {"format": "fernet-v1", "agent_id": self.config.agent_id,
                    "ciphertext": self.cipher.encrypt(encoded).decode("ascii")}
        return {"format": "json-v1", "data": measurements}

    async def run(self) -> None:
        if not self.config.telemetry_url:
            return
        timeout = aiohttp.ClientTimeout(total=8)
        headers = {"Authorization": f"Bearer {self.config.telemetry_token}"}
        backoff = 1
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                try:
                    async with session.post(self.config.telemetry_url, json=self.make_payload(),
                                            headers=headers) as response:
                        response.raise_for_status()
                        LOGGER.info("Telemetry sent successfully (HTTP %s)", response.status)
                        backoff = 1
                        await asyncio.sleep(self.config.interval_seconds)
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    LOGGER.warning("Telemetry delivery failed: %s; retrying", type(exc).__name__)
                    await asyncio.sleep(min(self.config.interval_seconds * backoff, 60))
                    backoff = min(backoff * 2, 16)

    def start(self) -> None:
        if self.config.telemetry_url:
            self._task = asyncio.create_task(self.run(), name="lumos-telemetry")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
