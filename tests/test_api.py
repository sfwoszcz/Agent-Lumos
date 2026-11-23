import pytest
from aiohttp.test_utils import TestClient, TestServer

from agent_lumos.api import AgentAPI


@pytest.mark.asyncio
async def test_full_auth_and_diagnostics(config):
    async with TestClient(TestServer(AgentAPI(config).create_app())) as client:
        health = await client.get('/health')
        assert health.status == 200
        assert (await health.json())["service"] == "agent-lumos"

        denied = await client.get('/v1/metrics')
        assert denied.status == 401

        wrong = await client.post('/v1/login', json={"username":"admin", "password":"wrong"})
        assert wrong.status == 401

        login = await client.post('/v1/login', json={"username":"admin", "password":"TestPassword!2026"})
        assert login.status == 200
        token = (await login.json())["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        metrics = await client.get('/v1/metrics', headers=headers)
        assert metrics.status == 200
        measurements = await metrics.json()
        for metric in ("cpu_percent", "memory_percent", "disk_percent", "uptime_seconds"):
            assert metric in measurements

        diagnostic = await client.post('/v1/diagnostics', headers=headers, json={"action":"whoami"})
        assert diagnostic.status == 200
        assert "username" in (await diagnostic.json())["result"]

        refused = await client.post('/v1/diagnostics', headers=headers,
                                    json={"action":"rm -rf /"})
        assert refused.status == 400
        assert "Unknown diagnostic" in (await refused.json())["error"]

        invalid = await client.post('/v1/diagnostics', headers=headers, data='not json')
        assert invalid.status == 400


@pytest.mark.asyncio
async def test_login_rate_limited(config):
    async with TestClient(TestServer(AgentAPI(config).create_app())) as client:
        for attempt in range(5):
            response = await client.post('/v1/login', json={"username":"admin", "password":"bad"})
            assert response.status == 401
        response = await client.post('/v1/login', json={"username":"admin", "password":"TestPassword!2026"})
        assert response.status == 429


@pytest.mark.asyncio
async def test_malformed_body(config):
    async with TestClient(TestServer(AgentAPI(config).create_app())) as client:
        response = await client.post('/v1/login', json=["admin", "password"])
        assert response.status == 400
