"""CLI orchestration for a transparent, reproducible ML learning demo."""
from __future__ import annotations
import json
import sys
from .ml import (SensorAnomalyDetector, SensorObservation, evaluation_report,
                 synthetic_dataset, threshold_alarm)
from .stm32 import InvalidFrame, MAX_FRAME_BYTES, parse_frame


def main(stdin_frames: bool = False) -> int:
    if not stdin_frames:
        print(json.dumps(evaluation_report(), indent=2, sort_keys=True))
        return 0

    # This is *not* labeled evaluation; samples come from the simulator or a
    # device. Train synthetic normal reference data, score incoming observations.
    model = SensorAnomalyDetector().fit(synthetic_dataset().training)
    count, missing, rejected = 0, 0, 0
    for line in sys.stdin.buffer:
        if count + missing + rejected >= 10000:
            raise ValueError("Input line budget exceeded")
        if len(line) > MAX_FRAME_BYTES:
            rejected += 1
            continue
        try:
            frame = parse_frame(line)
        except InvalidFrame:
            rejected += 1
            continue
        if frame.temperature_c is None or frame.vdd_mv is None:
            missing += 1
            continue
        observation = SensorObservation(float(frame.vdd_mv), frame.temperature_c)
        result = model.score([observation])[0]
        print(json.dumps({"device_id": frame.device_id, "sequence": frame.sequence,
                          "vdd_mv":frame.vdd_mv,"temperature_c":frame.temperature_c,
                          "cpp_state":frame.state,"rule_alarm":threshold_alarm(observation),
                          "ml_anomaly": result.predicted_anomaly,
                          "anomaly_score":round(result.anomaly_score, 5),
                          "authenticated":False,
                          "data_origin":"untrusted UART/simulator"}, sort_keys=True))
        count += 1
    print(json.dumps({"scored":count,"missing_sensors":missing,"rejected":rejected}),file=sys.stderr)
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agent Lumos host-side anomaly demo")
    parser.add_argument("--stdin-frames", action="store_true", help="Score validated STM32 protocol lines from stdin")
    main(**vars(parser.parse_args()))
