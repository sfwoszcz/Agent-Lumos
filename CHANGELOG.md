# Changelog

All notable changes to Agent Lumos are documented here.

## [1.2.0] - 2026-11-23
### Added
- CMake native C11/C++17 simulator and CTest test targets.
- Makefile shortcuts and CMake presets, including optional host sanitizers.
- x86-64 ABI assembly exercise and AArch64 learning example.
- Host-side machine-learning anomaly detection with an IsolationForest baseline.
- Reproducible synthetic ML evaluation and simulator frame scoring.
- Linux documentation, CI workflows, STM32 UART protocol and read-only diagnostic APIs.

### Security and limitations
- Authentication, safe read-only diagnostics and secure defaults are retained.
- No remotely supplied arbitrary shell commands.
- STM32 full firmware has **not** been validated on physical hardware.
- ML measurements use synthetic data and are **not** evidence of real-world intrusion detection.
- Educational prototype, not a production-ready monitoring or security product.
