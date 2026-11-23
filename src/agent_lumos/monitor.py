"""Read-only device observations and named diagnostics; never execute a shell."""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
from pathlib import Path
import platform
import socket

import psutil


class SystemMonitor:
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.disk_root = str(Path.home().anchor or "/")
        psutil.cpu_percent(interval=None)  # Prime the non-blocking CPU measurement.

    def collect(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage(self.disk_root).percent,
            "uptime_seconds": max(0, int(datetime.now(timezone.utc).timestamp() - psutil.boot_time())),
        }

    def diagnostic(self, action: str) -> dict:
        """Return only the read-only diagnostics explicitly defined here."""
        if action == "whoami":
            return {"username": getpass.getuser()}
        if action == "uptime":
            return {"uptime_seconds": max(0, int(datetime.now(timezone.utc).timestamp() - psutil.boot_time()))}
        if action == "disk":
            disk = psutil.disk_usage(self.disk_root)
            return {"path": self.disk_root, "total_bytes": disk.total, "free_bytes": disk.free,
                    "used_percent": disk.percent}
        if action == "platform":
            return {"system": platform.system(), "release": platform.release(), "machine": platform.machine()}
        raise ValueError("Unknown diagnostic action. Allowed: whoami, uptime, disk, platform")
