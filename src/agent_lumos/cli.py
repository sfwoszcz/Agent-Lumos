"""Initialize credentials, launch the agent, or run a local demo receiver."""

from __future__ import annotations

import argparse
import getpass
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import ssl
import sys

from aiohttp import web
from cryptography.fernet import Fernet

from .api import AgentAPI
from .config import AgentConfig, load_env_file
from .demo_receiver import DemoReceiver
from .security import PasswordHasher
from .stm32 import MAX_FRAME_BYTES, InvalidFrame, STM32Registry


def make_config_file(path: Path, password: str) -> None:
    """Atomically create an owner-readable secrets file. Never overwrite one."""
    digest = PasswordHasher.hash_password(password)
    config = (
        "# Local development secrets. Do not commit this file.\n"
        "LUMOS_HOST=127.0.0.1\n"
        "LUMOS_PORT=8765\n"
        "LUMOS_USERNAME=admin\n"
        "LUMOS_AGENT_ID=lumos-local\n"
        f"LUMOS_JWT_SECRET={secrets.token_urlsafe(48)}\n"
        f"LUMOS_ADMIN_PASSWORD_HASH={digest}\n"
        "LUMOS_SEND_INTERVAL=15\n"
        "LUMOS_TELEMETRY_URL=\n"
        f"LUMOS_TELEMETRY_TOKEN={secrets.token_urlsafe(32)}\n"
        f"LUMOS_FERNET_KEY={Fernet.generate_key().decode('ascii')}\n"
        "LUMOS_LOG_FILE=agent_lumos.log\n"
        "# Optional STM32 UART: LUMOS_STM32_PORT=/dev/ttyACM0\n"
        "LUMOS_STM32_BAUD=115200\n"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as outfile:
        outfile.write(config)


def init(args: argparse.Namespace) -> None:
    pw = getpass.getpass("Create admin password (12+ characters): ")
    again = getpass.getpass("Confirm password: ")
    if pw != again:
        raise ValueError("Passwords do not match")
    make_config_file(args.env_file, pw)
    print(f"Created {args.env_file} with owner-only permissions and a hashed password.")
    print("Keep this file private. Run: agent-lumos serve")


def configure_logging(path: Path) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)
    file_handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def read_stm32(args: argparse.Namespace) -> None:
    """Observe UART frames on stdin or a local serial port; never transmit."""
    import json
    registry = STM32Registry()
    input_stream = None
    try:
        if args.stdin:
            input_stream = sys.stdin.buffer
        else:
            try:
                import serial
            except ImportError as exc:
                raise ValueError("Install optional serial dependency: pip install '.[stm32]'") from exc
            input_stream = serial.Serial(port=args.port, baudrate=args.baud, timeout=1.0)
        accepted = 0
        while accepted < args.max_frames:
            raw = input_stream.readline(MAX_FRAME_BYTES + 1)
            if not raw:
                if args.stdin:
                    break
                continue
            try:
                row = registry.ingest(raw)
            except InvalidFrame as exc:
                print(f"[reject] {exc}", file=sys.stderr)
                continue
            if row is not None:
                print(json.dumps(row, sort_keys=True), flush=True)
                accepted += 1
    finally:
        if not args.stdin and input_stream is not None:
            input_stream.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent-lumos", description="Agent Lumos educational RMM agent")
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "serve", "demo-receiver"):
        sub = subs.add_parser(command)
        sub.add_argument("--env-file", type=Path, default=Path(".env"), help="Private configuration file")
    bridge = subs.add_parser("stm32-read", help="Read-only STM32 UART bridge")
    source = bridge.add_mutually_exclusive_group(required=True)
    source.add_argument("--stdin", action="store_true", help="Read frames from stdin (simulator)")
    source.add_argument("--port", help="Serial port, e.g. /dev/ttyACM0")
    bridge.add_argument("--baud", type=int, default=115200)
    bridge.add_argument("--max-frames", type=int, default=4)
    ml = subs.add_parser("ml-demo", help="Evaluate a host-side telemetry anomaly model")
    ml.add_argument("--stdin-frames", action="store_true", help="Score UART frames from stdin")
    args = parser.parse_args()

    try:
        if args.command == "ml-demo":
            from .ml_demo import main as ml_main
            ml_main(stdin_frames=args.stdin_frames)
            return
        if args.command == "stm32-read":
            if not 1200 <= args.baud <= 1000000 or not 1 <= args.max_frames <= 100000:
                raise ValueError("Invalid serial baud or --max-frames")
            read_stm32(args)
            return
        if args.command == "init":
            init(args)
            return
        load_env_file(args.env_file)
        config = AgentConfig.from_env()
        configure_logging(config.log_file)
        if args.command == "serve":
            ssl_ctx = None
            if config.tls_cert and config.tls_key:
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                ssl_ctx.load_cert_chain(str(config.tls_cert), str(config.tls_key))
            logging.info("Agent Lumos starting on %s:%s", config.host, config.port)
            web.run_app(AgentAPI(config).create_app(), host=config.host, port=config.port,
                        ssl_context=ssl_ctx, print=None)
        elif args.command == "demo-receiver":
            logging.warning("Demo receiver: localhost only; do not expose to a network")
            web.run_app(DemoReceiver(config).create_app(), host="127.0.0.1", port=8766, print=None)
    except (ValueError, OSError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
