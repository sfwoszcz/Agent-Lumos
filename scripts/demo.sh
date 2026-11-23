#!/usr/bin/env bash
# Read-only terminal tour: agent must already be running on localhost.
set -euo pipefail
BASE_URL="${LUMOS_DEMO_URL:-http://127.0.0.1:8765}"
USER="${LUMOS_DEMO_USERNAME:-admin}"
PASSWORD="${LUMOS_DEMO_PASSWORD:-}"

printf '\n'
printf '  +------------------------------------------------+\n'
printf '  |  * AGENT LUMOS *  //  Linux live demo          |\n'
printf '  |  observe. authenticate. diagnose.             |\n'
printf '  +------------------------------------------------+\n\n'

printf '[1/4] Health check (public)\n$ curl -s %s/health\n' "$BASE_URL"
curl --silent --show-error --fail "${BASE_URL}/health" | python -m json.tool
printf '\n[2/4] Access denied without a token\n$ curl ... /v1/metrics\n'
STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' "${BASE_URL}/v1/metrics")"
printf 'HTTP %s (expected 401)\n' "$STATUS"
if [ "$STATUS" != 401 ]; then
    printf 'Expected HTTP 401, got %s\n' "$STATUS" >&2
    exit 1
fi
if [ -z "$PASSWORD" ]; then
    printf '\nAdministrator password: '
    IFS= read -r -s PASSWORD
    printf '\n'
fi

printf '\n[3/4] Authenticate with JWT (token hidden)\n$ POST /v1/login\n'
LOGIN_RESPONSE="$(printf '%s' "$PASSWORD" \
    | python -c 'import json,sys; print(json.dumps({"username":sys.argv[1], "password":sys.stdin.read()}))' "$USER" \
    | curl --silent --show-error --fail -X POST "${BASE_URL}/v1/login" \
        -H 'Content-Type: application/json' --data-binary @-)"
TOKEN="$(printf '%s' "$LOGIN_RESPONSE" | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
unset PASSWORD LOGIN_RESPONSE
printf 'JWT issued (not printed)\n'

printf '\n[4/4] Protected system metrics\n$ GET /v1/metrics (Bearer JWT)\n'
curl --silent --show-error --fail "${BASE_URL}/v1/metrics" \
    -H "Authorization: Bearer ${TOKEN}" | python -m json.tool
printf '\nRead-only diagnostic: whoami\n$ POST /v1/diagnostics {"action":"whoami"}\n'
curl --silent --show-error --fail -X POST "${BASE_URL}/v1/diagnostics" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    --data '{"action":"whoami"}' | python -m json.tool
unset TOKEN
printf '\n[OK] Agent Lumos demo complete. No shell commands were executed on the agent.\n'
