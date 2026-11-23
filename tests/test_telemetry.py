from dataclasses import replace

from aiohttp.test_utils import TestClient, TestServer
from cryptography.fernet import Fernet
import pytest

from agent_lumos.demo_receiver import DemoReceiver
from agent_lumos.monitor import SystemMonitor
from agent_lumos.telemetry import TelemetryReporter


@pytest.mark.asyncio
async def test_fernet_telemetry_receiver(config):
    cfg = replace(config, fernet_key=Fernet.generate_key().decode())
    payload = TelemetryReporter(cfg, SystemMonitor(cfg.agent_id)).make_payload()
    assert payload["format"] == "fernet-v1"
    assert "cpu_percent" not in payload
    async with TestClient(TestServer(DemoReceiver(cfg).create_app())) as client:
        denied = await client.post('/v1/report', json=payload)
        assert denied.status == 401
        accepted = await client.post('/v1/report', json=payload, headers={"Authorization": "Bearer " + cfg.telemetry_token})
        assert accepted.status == 200
        assert (await accepted.json())["accepted"]
        tampered = await client.post('/v1/report', json={**payload, "ciphertext":"invalid"},
                                     headers={"Authorization": "Bearer " + cfg.telemetry_token})
        assert tampered.status == 400


def test_read_only_monitor(config):
    monitor = SystemMonitor(config.agent_id)
    assert isinstance(monitor.diagnostic("disk")["free_bytes"], int)
    assert monitor.diagnostic("platform")["system"]
    with pytest.raises(ValueError):
        monitor.diagnostic("ls")
