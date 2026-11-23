# Agent Lumos — Linux terminal walkthrough

This walkthrough uses a single machine. It is safe for a local learning lab and runs **read-only diagnostic functions** rather than arbitrary commands.

## Prerequisites

```bash
python3 --version   # Requires 3.11 or newer
curl --version
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
agent-lumos init
```

Choose a unique 12+ character password when prompted. **Do not share or commit your `.env` file.**

## Terminal 1 — launch the local agent

```bash
agent-lumos serve
```

Expected startup behavior: a logging line saying it listens at `127.0.0.1:8765`. The process will keep running until you press `Ctrl+C`.

## Terminal 2 — interactive showcase

```bash
source .venv/bin/activate
./scripts/demo.sh
```

This runs, in order:

1. Public health check (`200 OK`).
2. Protected metrics without a JWT (`401 Unauthorized`).
3. Administrator login (`POST /v1/login`), with the access token hidden.
4. Authenticated metrics and `whoami` diagnostic (JSON responses).

The tested result (host and user anonymized) is in [demo-output.txt](demo-output.txt). Your CPU/disk/RAM readings and uptime will differ.

## Manual `curl` commands (optional)

**Health:**

```bash
curl -s http://127.0.0.1:8765/health | python -m json.tool
```

**Reject a request without JWT:**

```bash
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8765/v1/metrics
# HTTP 401
```

**Login:** Use the interactive `./scripts/demo.sh` to avoid accidentally placing a password or bearer token in your terminal history. The following is only an explanation of the login API payload; replace placeholders locally:

```json
{"username":"admin","password":"<your private password>"}
```

**Diagnostics** (JWT must be included in the request header):

```json
{"action":"uptime"}
```

Supported actions: `whoami`, `uptime`, `disk`, `platform`. The agent intentionally rejects arbitrary shell commands.

## Live encrypted telemetry (optional)

Start a local receiver in one terminal:

```bash
agent-lumos demo-receiver
```

Then start the agent in another terminal:

```bash
LUMOS_TELEMETRY_URL=http://127.0.0.1:8766/v1/report \
LUMOS_SEND_INTERVAL=2 agent-lumos serve
```

Example of output captured in a local smoke test:

```text
[agent]    Telemetry sent successfully (HTTP 200)
[receiver] Received lumos-local telemetry: cpu=0.3% memory=22.1%
```

Because `.env` contains a Fernet key, the outbound JSON is encrypted before being delivered. The local-only receiver decrypts it. For real remote monitoring, configure a **trusted HTTPS** receiver and a secure service deployment.

## Stop and verify

Press `Ctrl+C` in each running terminal, then run:

```bash
python -m pytest -q
# 26 passed (verified on Linux for v1.1.0)
```

## STM32 extension demonstration

Run `./scripts/stm32_demo.sh` to see the C/C++-to-Python STM32 pipeline. It needs a C/C++ compiler but no physical STM32 board. See [STM32.md](STM32.md).

## Safety reminder

Agent Lumos is an educational proof of concept. Do not expose the demo receiver to the Internet or use this version for unattended privileged administration.
