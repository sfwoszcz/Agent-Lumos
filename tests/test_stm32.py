"""STM32 telemetry: strict parsing, replay handling, and C/Python cross-language test."""

from pathlib import Path
import shutil
import subprocess

import pytest
from aiohttp.test_utils import TestClient, TestServer

from agent_lumos.api import AgentAPI
from agent_lumos.stm32 import (InvalidFrame, STM32Frame, STM32Registry,
                              crc16_ccitt, encode_frame, parse_frame)

ROOT = Path(__file__).resolve().parents[1]


def test_crc_reference_vector():
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_round_trip_and_unknown_sensors():
    frame = STM32Frame("nucleo-f446re", 1, 1000, None, None, "unknown")
    raw = encode_frame(frame)
    assert raw.startswith(b"LUMOS1,nucleo-f446re,1,1000,NA,NA,unknown,")
    assert parse_frame(raw) == frame


def test_round_trip_negative_temperature():
    frame = STM32Frame("lab-stm32", 42, 1234, 3200, -1.25, "warn")
    assert parse_frame(encode_frame(frame)) == frame


@pytest.mark.parametrize("raw", [
    b"A" * 161,
    b"LUMOS1,stm32,1,2,3300,2500,ok,0000\n",  # wrong CRC
    b"LUMOS1,x\xff,1,2,NA,NA,unknown,0000\n",  # invalid ASCII
    b"LUMOS2,board,1,2,NA,NA,unknown,0000\n",  # unknown version
    b"LUMOS1,board,1,2,NA,NA,unknown,0000\nextra",  # line injection
    b"LUMOS1,board,1,2,NA,NA,unknown,0000",  # missing terminator
])
def test_invalid_frames_rejected(raw):
    with pytest.raises(InvalidFrame):
        parse_frame(raw)


def test_invalid_but_crc_valid_fields():
    for frame in (
        STM32Frame("../bad", 1, 1000, 3300, 20, "ok"),
        STM32Frame("good", -1, 1000, 3300, 20, "ok"),
        STM32Frame("good", 1, 1000, 9000, 20, "ok"),
        STM32Frame("good", 1, 1000, 3300, 155.0, "ok"),
        STM32Frame("good", 1, 1000, 3300, 20, "critical"),
    ):
        with pytest.raises(ValueError):
            encode_frame(frame)


def test_registry_sequence_and_reboot():
    registry = STM32Registry(max_devices=1)
    start = STM32Frame("board", 3, 4000, 3300, 24.0, "ok")
    assert registry.ingest(encode_frame(start))["sequence"] == 3
    assert registry.ingest(encode_frame(start)) is None
    assert registry.ingest(encode_frame(STM32Frame("board", 2, 3000, 3300, 24, "ok")))["sequence"] == 2
    registry.ingest(encode_frame(STM32Frame("newboard", 1, 100, None, None, "unknown")))
    assert len(registry.snapshot()) == 1
    assert registry.snapshot()[0]["device_id"] == "newboard"
    assert registry.snapshot()[0]["authenticated"] is False


@pytest.mark.asyncio
async def test_stm32_route_requires_jwt(config):
    api = AgentAPI(config)
    api.stm32.ingest(encode_frame(STM32Frame("nucleo", 1, 1000, None, None, "unknown")))
    async with TestClient(TestServer(api.create_app())) as client:
        response = await client.get("/v1/stm32/devices")
        assert response.status == 401
        response = await client.post('/v1/login', json={"username": "admin", "password": "TestPassword!2026"})
        assert response.status == 200
        token = (await response.json())["access_token"]
        response = await client.get("/v1/stm32/devices", headers={"Authorization": f"Bearer {token}"})
        assert response.status == 200
        payload = await response.json()
        assert payload["count"] == 1
        assert payload["devices"][0]["device_id"] == "nucleo"


def test_real_c_encoder_and_cpp_simulator(tmp_path):
    if not shutil.which("gcc") or not shutil.which("g++"):
        pytest.skip("GCC/G++ are not installed")
    firmware = ROOT / "firmware/stm32"
    common = ["-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{firmware / 'include'}"]
    obj = tmp_path / "protocol.o"
    exe = tmp_path / "simulator"
    subprocess.run(["gcc", "-std=c11", *common, "-c", str(firmware / "src/lumos_protocol.c"), "-o", str(obj)], check=True)
    subprocess.run(["g++", "-std=c++17", *common, str(firmware / "native/health_policy.cpp"),
                    str(firmware / "native/simulator.cpp"), str(obj), "-o", str(exe)], check=True)
    run = subprocess.run([str(exe)], capture_output=True, check=True)
    frames = [parse_frame(raw) for raw in run.stdout.splitlines(keepends=True)]
    assert len(frames) == 4
    assert [frame.state for frame in frames] == ["ok", "ok", "warn", "ok"]
    assert frames[2].temperature_c == 74.8
    assert all(frame.device_id == "stm32-sim" for frame in frames)
