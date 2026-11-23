"""Bounded, read-only STM32 UART telemetry intake for Agent Lumos.

CRC-16/CCITT-FALSE detects accidental corruption; it is NOT authentication.
Treat all board-originated values as untrusted observations.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any

LOGGER = logging.getLogger(__name__)
MAX_FRAME_BYTES = 160
MAX_DEVICES = 32
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,24}\Z")
UNSIGNED_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,9})\Z")
SIGNED_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]{0,5})\Z")
CRC_PATTERN = re.compile(r"[0-9A-F]{4}\Z")
STATES = frozenset({"ok", "warn", "unknown"})


class InvalidFrame(ValueError):
    """A malformed or corrupted telemetry line was rejected."""


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE: polynomial 0x1021, init 0xFFFF, no xor-out."""
    crc = 0xFFFF
    for octet in data:
        crc ^= octet << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class STM32Frame:
    device_id: str
    sequence: int
    uptime_ms: int
    vdd_mv: int | None
    temperature_c: float | None
    state: str


def _unsigned(part: str) -> int:
    if not UNSIGNED_PATTERN.fullmatch(part):
        raise InvalidFrame("Invalid unsigned integer")
    number = int(part)
    if number > 0xFFFFFFFF:
        raise InvalidFrame("Integer exceeds 32-bit range")
    return number


def parse_frame(raw: bytes | str) -> STM32Frame:
    """Parse a strictly bounded ASCII line, validating format, ranges and CRC."""
    if isinstance(raw, bytes):
        if len(raw) > MAX_FRAME_BYTES:
            raise InvalidFrame("Frame too long")
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise InvalidFrame("Frame must be ASCII") from exc
    else:
        if len(raw) > MAX_FRAME_BYTES or not raw.isascii():
            raise InvalidFrame("Frame too long or not ASCII")
        text = raw
    if not text.endswith("\n"):
        raise InvalidFrame("Incomplete UART line")
    text = text.removesuffix("\n").removesuffix("\r")
    fields = text.split(",")
    if len(fields) != 8 or fields[0] != "LUMOS1":
        raise InvalidFrame("Unsupported telemetry frame")
    version, device_id, sequence, uptime, vdd, temp, state, claimed_crc = fields
    if not ID_PATTERN.fullmatch(device_id):
        raise InvalidFrame("Invalid device ID")
    if not CRC_PATTERN.fullmatch(claimed_crc):
        raise InvalidFrame("Malformed CRC")
    actual_crc = crc16_ccitt(",".join(fields[:-1]).encode("ascii"))
    if actual_crc != int(claimed_crc, 16):
        raise InvalidFrame("CRC mismatch")
    seq_value, uptime_value = _unsigned(sequence), _unsigned(uptime)
    vdd_value = None if vdd == "NA" else _unsigned(vdd)
    if vdd_value is not None and not 1800 <= vdd_value <= 5500:
        raise InvalidFrame("Supply voltage outside expected range")
    if temp == "NA":
        temperature = None
    else:
        if not SIGNED_PATTERN.fullmatch(temp):
            raise InvalidFrame("Invalid temperature")
        centi = int(temp)
        if not -4000 <= centi <= 12500:
            raise InvalidFrame("Temperature outside expected range")
        temperature = centi / 100.0
    if state not in STATES:
        raise InvalidFrame("Unknown state")
    return STM32Frame(device_id, seq_value, uptime_value, vdd_value, temperature, state)


def encode_frame(frame: STM32Frame) -> bytes:
    """Reference encoder for host-side tests; MCU encoder is implemented in C."""
    if not ID_PATTERN.fullmatch(frame.device_id) or frame.state not in STATES:
        raise ValueError("Invalid device or state")
    if not 0 <= frame.sequence <= 0xFFFFFFFF or not 0 <= frame.uptime_ms <= 0xFFFFFFFF:
        raise ValueError("Invalid counter")
    vdd = "NA" if frame.vdd_mv is None else str(frame.vdd_mv)
    temperature = "NA" if frame.temperature_c is None else str(round(frame.temperature_c * 100))
    prefix = f"LUMOS1,{frame.device_id},{frame.sequence},{frame.uptime_ms},{vdd},{temperature},{frame.state}"
    encoded = f"{prefix},{crc16_ccitt(prefix.encode('ascii')):04X}\n".encode("ascii")
    if len(encoded) > MAX_FRAME_BYTES:
        raise ValueError("Frame too long")
    if parse_frame(encoded) != frame:
        raise ValueError("Invalid frame values")
    return encoded


class STM32Registry:
    """Retain a bounded in-memory snapshot of latest *received* MCU observations."""

    def __init__(self, max_devices: int = MAX_DEVICES) -> None:
        self._latest: dict[str, dict[str, Any]] = {}
        self.max_devices = max_devices

    def ingest(self, raw: bytes | str) -> dict[str, Any] | None:
        frame = parse_frame(raw)
        previous = self._latest.get(frame.device_id)
        if previous:
            # Ignore replays, but allow a counter reset following an uptime reset.
            rebooted = frame.uptime_ms < previous["uptime_ms"]
            if not rebooted and frame.sequence <= previous["sequence"]:
                return None
        entry = {**asdict(frame),
                 "last_seen": datetime.now(timezone.utc).isoformat(),
                 "integrity": "crc16-error-check-only",
                 "authenticated": False}
        if frame.device_id not in self._latest and len(self._latest) >= self.max_devices:
            self._latest.pop(next(iter(self._latest)))
        self._latest[frame.device_id] = entry
        return entry.copy()

    def snapshot(self) -> list[dict[str, Any]]:
        return [row.copy() for row in self._latest.values()]


async def collect_serial(port: str, baudrate: int, registry: STM32Registry) -> None:
    """Read serial input in a thread and reconnect if unplugged; NEVER send commands."""
    try:
        import serial  # optional extra: python -m pip install '.[stm32]'
    except ImportError as exc:
        LOGGER.error("pyserial is required for STM32 UART integration: pip install '.[stm32]'")
        raise RuntimeError("pyserial is not installed") from exc

    while True:
        try:
            LOGGER.info("STM32 UART collector opening %s at %d baud", port, baudrate)
            with serial.Serial(port=port, baudrate=baudrate, timeout=0.25) as device:
                while True:
                    line = await asyncio.to_thread(device.readline, MAX_FRAME_BYTES + 1)
                    if not line:
                        await asyncio.sleep(0)
                        continue
                    try:
                        entry = registry.ingest(line)
                        if entry:
                            LOGGER.info("STM32 observation from %s (seq=%d)",
                                        entry["device_id"], entry["sequence"])
                    except InvalidFrame as exc:
                        LOGGER.warning("Rejected STM32 UART line: %s", exc)
        except asyncio.CancelledError:
            raise
        except (OSError, ValueError, serial.SerialException) as exc:
            LOGGER.warning("STM32 UART unavailable (%s); reconnecting", type(exc).__name__)
            await asyncio.sleep(2)
