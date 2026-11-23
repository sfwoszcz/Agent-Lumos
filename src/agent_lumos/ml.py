"""Host-side, reproducible STM32 telemetry anomaly detection (educational only).

IsolationForest is *not* an intrusion detector. It scores unusual numeric sensor
values, not identities, malicious intent, exploitation, or compromise.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SensorObservation:
    vdd_mv: float
    temperature_c: float

    def __post_init__(self) -> None:
        if not (isfinite(self.vdd_mv) and isfinite(self.temperature_c)):
            raise ValueError("Sensor values must be finite")
        if not (1800 <= self.vdd_mv <= 5500 and -40 <= self.temperature_c <= 125):
            raise ValueError("Sensor values outside STM32 protocol range")


def threshold_alarm(reading: SensorObservation) -> bool:
    """Independent, interpretable baseline, matching C++ health thresholds."""
    return reading.vdd_mv < 3200 or reading.temperature_c > 70.0


@dataclass(frozen=True)
class ScoredObservation:
    reading: SensorObservation
    anomaly_score: float  # Higher is more anomalous; zero is the decision boundary.
    predicted_anomaly: bool


class SensorAnomalyDetector:
    """Host-side sklearn model with fixed schema; no untrusted model deserialization.

    Train only on observations designated healthy *before* evaluating later samples.
    Fit is deliberately separate from scoring to avoid train/test leakage.
    """

    def __init__(self, contamination: float = 0.02, seed: int = 42) -> None:
        if not 0.0 < contamination <= 0.5:
            raise ValueError("contamination must be in (0, 0.5]")
        self._seed = seed
        self._contamination = contamination
        self._pipeline = None

    def fit(self, training: Sequence[SensorObservation]) -> SensorAnomalyDetector:
        if len(training) < 100:
            raise ValueError("At least 100 normal readings required for demonstration")
        from sklearn.ensemble import IsolationForest
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        pipeline = make_pipeline(
            StandardScaler(),
            IsolationForest(n_estimators=150, contamination=self._contamination,
                            random_state=self._seed, n_jobs=1),
        )
        pipeline.fit([(r.vdd_mv, r.temperature_c) for r in training])
        self._pipeline = pipeline
        return self

    def score(self, readings: Sequence[SensorObservation]) -> list[ScoredObservation]:
        if self._pipeline is None:
            raise RuntimeError("Fit the model before scoring")
        if not readings:
            return []
        values = [(r.vdd_mv, r.temperature_c) for r in readings]
        scores = self._pipeline.decision_function(values)
        return [ScoredObservation(r, float(-score), bool(score < 0))
                for r, score in zip(readings, scores)]


@dataclass(frozen=True)
class SyntheticDataset:
    training: tuple[SensorObservation, ...]
    evaluation: tuple[SensorObservation, ...]
    labels: tuple[bool, ...]  # True = injected abnormal sensor data.


def synthetic_dataset(seed: int = 2026) -> SyntheticDataset:
    """Create a deterministic train/evaluation split for honest demos.

    This is a synthetic *sensor deviation* task, not malware/attack detection.
    In particular, training samples are never reused for evaluation.
    """
    import numpy as np
    rng = np.random.default_rng(seed)

    def normal(n: int) -> list[SensorObservation]:
        v = rng.normal(3300, 18, size=n)
        t = rng.normal(28, 2.5, size=n)
        return [SensorObservation(float(a), float(b)) for a, b in zip(v, t)]

    train = normal(400)
    holdout = normal(120)
    low_vdd = [SensorObservation(float(v), float(t)) for v, t in zip(
        rng.normal(3140, 25, size=35), rng.normal(29, 2.5, size=35))]
    thermal = [SensorObservation(float(v), float(t)) for v, t in zip(
        rng.normal(3290, 18, size=35), rng.normal(53, 6, size=35))]
    eval_records = holdout + low_vdd + thermal
    flags = [False] * len(holdout) + [True] * (len(low_vdd) + len(thermal))
    order = rng.permutation(len(eval_records)).tolist()
    return SyntheticDataset(tuple(train), tuple(eval_records[i] for i in order),
                            tuple(flags[i] for i in order))


def confusion(y_true: Sequence[bool], y_pred: Sequence[bool]) -> dict[str, int | float]:
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("Equal non-empty label vectors required")
    tp = sum(bool(a) and bool(b) for a, b in zip(y_true, y_pred))
    tn = sum(not a and not b for a, b in zip(y_true, y_pred))
    fp = sum(not a and bool(b) for a, b in zip(y_true, y_pred))
    fn = sum(bool(a) and not b for a, b in zip(y_true, y_pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp":tp,"tn":tn,"fp":fp,"fn":fn,
            "precision":round(precision, 3),"recall":round(recall, 3),"f1":round(f1, 3)}


def evaluation_report(seed: int = 2026) -> dict:
    ds = synthetic_dataset(seed)
    model = SensorAnomalyDetector().fit(ds.training)
    labels = [x.predicted_anomaly for x in model.score(ds.evaluation)]
    return {"data": "synthetic sensor measurements (NOT security incidents)",
            "model": "StandardScaler + IsolationForest",
            "features": ["vdd_mv", "temperature_c"],
            "train_size": len(ds.training), "eval_size": len(ds.evaluation),
            "injected_abnormal_samples": sum(ds.labels),
            "rule": confusion(ds.labels, [threshold_alarm(r) for r in ds.evaluation]),
            "ml": confusion(ds.labels, labels),
            "warning": "Anomaly != attack. Results on fabricated data cannot establish real-world detection performance."}
