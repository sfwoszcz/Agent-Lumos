# Security policy and threat model

Agent Lumos is an **educational demonstration**, not a production enterprise RMM.
Run it only on devices you own or are explicitly authorized to administer.

## Security choices

- **No remote shell or file manipulation.** `/v1/diagnostics` accepts only four fixed, read-only action IDs: `whoami`, `uptime`, `disk`, `platform`. There is no use of `subprocess`, `eval`, or `shell=True`.
- **Secure credential setup.** `agent-lumos init` generates a random JWT signing secret, a random telemetry bearer token, a Fernet key, and an administrator password hash using PBKDF2-HMAC-SHA256 with unique salt. Only the password hash is stored in `.env`; the password itself is not.
- **15-minute JWTs.** Tokens are signed with HS256 and validated for issuer, audience, signature, expiry, required claims, and requested scope. Keep JWTs secret; they are bearer credentials.
- **Localhost by default.** Binding the API to a public/nonloopback interface requires TLS certificate and key. Prefer a VPN, trusted proxy, or mutual TLS rather than exposing the API to the Internet.
- **Encrypted telemetry.** Remote metrics require HTTPS and a shared bearer token. Optional Fernet encrypts JSON contents as an additional protection layer. If a configured Fernet key is invalid, startup fails rather than silently sending plaintext.
- **Login limiting and logging.** Maximum five login attempts per 60 seconds per remote IP, in memory. Authentication failures and diagnostic requests are logged with rotation; passwords and tokens are not logged.
- **Ignored secrets.** `.env`/certificates and log files are excluded by `.gitignore`. Audit `git status` before publishing.

## STM32 device telemetry boundary

- The STM32 UART source is **untrusted input**. The gateway enforces ASCII, length, numeric ranges, and CRC checks before displaying observations. CRC is accidental-error detection, **not** device authentication, encryption, or anti-replay protection.
- The initial MCU example transmits only uptime and unknown sensors. UART ingestion is read-only and does not implement flashing, command execution, or firmware modification.
- The protected `/v1/stm32/devices` endpoint controls access to **view** readings with a scoped JWT. It does **not** establish a cryptographic identity for the MCU. Do not forward unverified serial frames as trustworthy security alerts.
- A hostile USB device, serial adapter, or local user with serial access could forge telemetry; isolate the lab, control device permissions, and do not expose the serial interface to untrusted hosts.
- Secure boot, signed updates, provisioning and device-side authentication are **not implemented**. Future STM32 security features depend on MCU family and hardware configuration.

## Important limitations

- Single administrator account; no multi-user RBAC, revocation list, MFA, password reset workflow, or key rotation automation. A stolen JWT remains usable until expiry.
- In-memory throttling is lost on restart and is not coordinated across multiple instances. Place a trusted rate-limiting proxy before remote deployments.
- No mutual TLS on the API, certificate pinning, robust central collector, durable queue, attestation, secure self-updates, or independent security audit.
- A hostname, process username and system statistics can be sensitive. Only send telemetry to servers you control.
- Local demo receiver is **not** a production deployment pattern: it binds only to `127.0.0.1` and accepts plain HTTP for demonstration.
- Reverse proxies need correct trust and authentication configuration; never rely on arbitrary forwarded IP headers.

## Reporting vulnerabilities

Please do not publish exploits against live deployments. Report privately to the repository maintainer via GitHub's private vulnerability reporting feature (if enabled), or by creating a non-sensitive issue asking for a private contact channel.

## Host-side ML threat model (v1.2)

The machine-learning demo scores **untrusted** STM32-style numeric telemetry using a reproducible synthetic baseline. The model does not authenticate MCU data or diagnose hostile activity. A forged CRC-valid serial frame can affect scores. Training on fabricated healthy samples, as done here, cannot establish detection efficacy on real hardware. The demo does not deserialize untrusted model artifacts. For evaluation details, see [docs/ML.md](docs/ML.md).
