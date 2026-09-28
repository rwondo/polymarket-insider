from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from conftest import make_trade

from src.features.feature_engineer import compute_features


def run_wallet(sizes):
    """Feed trades for one wallet through compute_features, carrying the stats forward."""
    wallet, features = None, None
    for size in sizes:
        features = compute_features(make_trade(size_usd=size), wallet)
        wallet = {
            "first_seen_at": features["first_seen_at"],
            "total_trades": features["total_trades"],
            "avg_trade_size": features["avg_trade_size"],
            "m2": features["m2"],
        }
    return wallet, features


def test_welford_matches_numpy():
    sizes = [12.0, 250.5, 3.2, 80.0, 41.7, 1000.0, 7.5]
    wallet, _ = run_wallet(sizes)

    assert wallet["total_trades"] == len(sizes)
    assert wallet["avg_trade_size"] == pytest.approx(np.mean(sizes))
    assert wallet["m2"] / (len(sizes) - 1) == pytest.approx(np.var(sizes, ddof=1))


def test_first_trade_from_wallet():
    features = compute_features(make_trade(size_usd=500.0), None)

    assert features["is_new_wallet"] is True
    assert features["size_z_score"] == 0.0
    assert features["days_since_first_seen"] == 0.0
    assert features["total_trades"] == 1


def test_z_score_needs_two_previous_trades():
    _, second = run_wallet([100.0, 5000.0])
    assert second["size_z_score"] == 0.0


def test_outlier_is_measured_against_previous_trades():
    # Previous trades: mean 100, sample std 10. A $1,000 trade is 90 std devs above.
    _, features = run_wallet([90.0, 100.0, 110.0, 1000.0])
    assert features["size_z_score"] == pytest.approx(90.0)


def test_identical_previous_trades_do_not_explode_the_z_score():
    # Seen in a live run: two "$500" trades that differ only by float noise, then a
    # $4,808 trade that scored a z of ~85 billion before the standard deviation floor
    _, features = run_wallet([499.99999995166667, 500.00000002372093, 4_807.83])
    assert features["size_z_score"] == pytest.approx(4_307.83)


def test_days_since_first_seen_accepts_naive_datetimes():
    # SQLite hands back naive datetimes; they are treated as UTC
    first_seen = datetime(2026, 1, 1)
    wallet = {"first_seen_at": first_seen, "total_trades": 1, "avg_trade_size": 10.0, "m2": 0.0}
    trade = make_trade(ts=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=3))

    assert compute_features(trade, wallet)["days_since_first_seen"] == pytest.approx(3.0)
