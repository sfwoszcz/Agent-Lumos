# Host-side ML: anomalous STM32 telemetry

Agent Lumos v1.2 demonstrates reproducible ML engineering, **not malware detection**.

## Objective

Detect numeric deviations in simulated MCU telemetry (`vdd_mv`, `temperature_c`) using a `StandardScaler` + `IsolationForest` pipeline from scikit-learn. The host-side Python process scores readings; **the model is not deployed to the STM32 MCU**.

## Reproduce the experiment

```bash
python -m pip install -e '.[dev,ml]'
make ml-demo
make ml-frames
```

`make ml-demo` trains on 400 synthetic healthy readings and evaluates 190 *separate* synthetic readings: 120 healthy, 35 low-supply-voltage deviations, and 35 moderately elevated-temperature deviations. It compares a fixed C++-aligned rule (`vdd_mv < 3200` or `temperature_c > 70`) with an IsolationForest anomaly score. A fixed random seed makes these specific results reproducible.

### Verified results from the synthetic holdout

| Method | TP | TN | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Threshold rules | 35 | 120 | 0 | 35 | 1.000 | 0.500 | 0.667 |
| IsolationForest | 70 | 119 | 1 | 0 | 0.986 | 1.000 | 0.993 |

**Do not present this as a real attack-detection score.** The distributions were deliberately created to highlight differences between simple rules and a learned baseline. Measuring generalization would require independently collected physical device telemetry, multiple devices, sensor calibration, operating regime variation, time series splits, and independent security incident labels where applicable.

## Simulator integration

```bash
make ml-frames
```

CMake compiles the C11 encoder and C++17 STM32 simulator. Python then validates UART frames with CRC, checks measurement presence and ranges, and scores them with an ML model trained on synthetic normal reference samples. Results include `cpp_state`, a boolean threshold alarm, a boolean ML anomaly indicator, and a numeric anomaly score. The frame output is explicitly marked **untrusted** and **unauthenticated**.

## Security and ML boundaries

- Sensor anomalies can be caused by legitimate load, temperature changes, hardware faults, or a malicious actor. A high anomaly score is **not evidence of exploitation**.
- UART CRC is not authentication; a local adversary with access to the serial link may forge valid readings.
- Only 2 telemetry features are modeled; there is no sequence model, concept-drift tracking, adversarial robustness, inference budget for MCU firmware, or network threat intelligence.
- The model is built in memory for the demo. There is **no loading of untrusted pickle/joblib model files**, reducing deserialization risk.
- For an honest portfolio, preserve the confusion matrices and explicitly discuss false positives, threat models, data provenance, and limitations.
