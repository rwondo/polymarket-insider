import numpy as np

from src.config import settings
from src.models.anomaly_detector import AnomalyDetector


def features(size=50.0, z=0.0, new=False, days=1.0, trades=5):
    return {
        "trade_size": size,
        "days_since_first_seen": days,
        "total_trades": trades,
        "size_z_score": z,
        "is_new_wallet": new,
    }


def trained_detector(seed=0):
    rng = np.random.default_rng(seed)
    n = 2_000
    rows = np.column_stack(
        [
            rng.lognormal(mean=3, sigma=1, size=n),  # trade size, median ~$20
            rng.uniform(0, 30, size=n),  # days since first seen
            rng.integers(1, 50, size=n),  # wallet trade count
            rng.normal(0, 1, size=n),  # z-score
        ]
    )
    detector = AnomalyDetector()
    detector.train(rows)
    return detector


def test_normal_trade_scores_zero_without_model():
    score, reasons = AnomalyDetector().score(features())
    assert score == 0
    assert reasons == []


def test_large_first_trade_rule():
    score, reasons = AnomalyDetector().score(features(size=25_000, new=True, days=0, trades=1))
    assert score == 40
    assert "First trade" in reasons[0]


def test_large_trade_from_known_wallet_does_not_trigger_new_wallet_rule():
    score, _ = AnomalyDetector().score(features(size=25_000, new=False))
    assert score == 0


def test_z_score_rule():
    score, reasons = AnomalyDetector().score(features(z=4.2))
    assert score == 30
    assert "4.2 standard deviations" in reasons[0]


def test_rules_alone_stay_below_threshold():
    # Alerts need the model to agree with a rule
    score, _ = AnomalyDetector().score(features(size=25_000, new=True, days=0, trades=1))
    assert score < settings.ANOMALY_THRESHOLD


def test_model_adds_points_for_outliers_only():
    detector = trained_detector()

    normal_score, normal_reasons = detector.score(features(size=20, days=10, trades=20))
    outlier_score, outlier_reasons = detector.score(features(size=50_000, z=40, days=0, trades=1))

    assert normal_score == 0 and normal_reasons == []
    assert outlier_score > 0
    assert any("Isolation Forest" in r for r in outlier_reasons)


def test_threshold_is_reachable_with_rule_and_model():
    detector = trained_detector()
    score, reasons = detector.score(features(size=50_000, new=True, days=0, trades=1))

    assert score >= settings.ANOMALY_THRESHOLD
    assert len(reasons) == 2


def test_retraining_replaces_the_model():
    detector = trained_detector(seed=0)
    first_model = detector.model
    detector.train(np.ones((10, 4)) * np.arange(10)[:, None])

    assert detector.model is not first_model
    assert detector.trained_on == 10
