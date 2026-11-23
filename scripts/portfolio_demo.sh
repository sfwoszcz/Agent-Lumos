#!/usr/bin/env bash
# Read-only, reproducible native simulation + host ML demonstration.
# Run from the repository root. Hardware STM32 validation is NOT performed.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

printf '\n[build] CMake + C11 + C++17 native simulator\n'
cmake --preset native >/dev/null
cmake --build --preset native --parallel >/dev/null
printf '[ok] Native build complete\n\n'

PYTHONPATH=src python3 - <<'PY'
import subprocess
from agent_lumos.stm32 import parse_frame
from agent_lumos.ml import (
    SensorAnomalyDetector, SensorObservation,
    evaluation_report, synthetic_dataset,
)

raw_frames = subprocess.check_output(["./build/native/stm32-sim"]).splitlines(keepends=True)
frames = [parse_frame(raw) for raw in raw_frames]
print('[stm32] CRC16-checked UART frames (HOST SIMULATION)')
for f in frames:
    label = 'WARN' if f.state == 'warn' else ' OK '
    print(f'  [{label}] seq={f.sequence:02d}  vdd={f.vdd_mv}mV  '
          f'temp={f.temperature_c:.2f}C')
print(f'[ok] {len(frames)} valid frames | device authentication: NO\n')

report = evaluation_report()
ml, rule = report['ml'], report['rule']
print('[ml] IsolationForest on SYNTHETIC sensor measurements')
print(f"  holdout={report['eval_size']}  injected={report['injected_abnormal_samples']}")
print(f"  ML:        recall={ml['recall']:.3f}  precision={ml['precision']:.3f}  FP={ml['fp']}  FN={ml['fn']}")
print(f"  threshold: recall={rule['recall']:.3f}  precision={rule['precision']:.3f}  FP={rule['fp']}  FN={rule['fn']}")
model = SensorAnomalyDetector().fit(synthetic_dataset().training)
for f in frames:
    if f.vdd_mv is None or f.temperature_c is None:
        continue
    score = model.score([SensorObservation(float(f.vdd_mv), f.temperature_c)])[0]
    if score.predicted_anomaly:
        print(f'  [ANOMALY] sim frame seq={f.sequence:02d} '
              f'vdd={f.vdd_mv}mV temp={f.temperature_c:.2f}C')
print('\n[done] Simulation complete. Anomaly != cyberattack.')
PY
