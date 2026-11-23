"""Reproducible model tests; no network or hardware required."""
import math
import pytest

pytest.importorskip("sklearn")
from agent_lumos.ml import (SensorObservation, SensorAnomalyDetector,
                            confusion, evaluation_report, synthetic_dataset,
                            threshold_alarm)


def test_synthetic_dataset_is_reproducible():
    assert synthetic_dataset() == synthetic_dataset()
    sample = synthetic_dataset()
    assert len(sample.training) == 400
    assert len(sample.evaluation) == 190
    assert sum(sample.labels) == 70
    assert all(not threshold_alarm(obs) for obs in sample.training)


def test_feature_validation_and_baseline():
    for value in (float("nan"), float("inf"), -50):
        with pytest.raises(ValueError):
            SensorObservation(3300, value)
    assert threshold_alarm(SensorObservation(3199, 25))
    assert not threshold_alarm(SensorObservation(3200, 70))


def test_fitting_and_scores_deterministic():
    dataset = synthetic_dataset()
    model = SensorAnomalyDetector().fit(dataset.training)
    assert model.score(dataset.evaluation) == SensorAnomalyDetector().fit(dataset.training).score(dataset.evaluation)
    assert len(model.score([])) == 0
    with pytest.raises(RuntimeError):
        SensorAnomalyDetector().score(dataset.evaluation)
    with pytest.raises(ValueError):
        SensorAnomalyDetector().fit(dataset.training[:8])


def test_synthetic_ml_evaluation_has_nontrivial_recall():
    report = evaluation_report()
    assert report["train_size"] == 400
    assert report["eval_size"] == 190
    assert report["injected_abnormal_samples"] == 70
    assert report["ml"]["recall"] > 0.8
    assert report["ml"]["f1"] > 0.8
    assert report["ml"]["tp"] > report["rule"]["tp"]
    assert sum(report["ml"][k] for k in ("tp","tn","fp","fn")) == 190


def test_confusion_metrics():
    assert confusion([True, False, False], [True, True, False])["precision"] == 0.5
    with pytest.raises(ValueError):
        confusion([], [])
