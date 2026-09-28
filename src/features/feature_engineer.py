import math
from datetime import UTC, datetime

# Features the Isolation Forest is trained on, in column order
ML_FEATURES = ("trade_size", "days_since_first_seen", "total_trades", "size_z_score")


def _as_utc(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def compute_features(trade: dict, wallet: dict | None) -> dict:
    """
    Build the features for one trade and the wallet's updated running stats.

    `wallet` holds the stats from the wallet's previous trades (None for a wallet this
    instance hasn't seen): first_seen_at, total_trades, avg_trade_size, m2.
    """
    size = trade["size_usd"]
    trade_time = _as_utc(trade["timestamp"])

    if wallet is None:
        n_prev, mean, m2, first_seen = 0, 0.0, 0.0, trade_time
    else:
        n_prev = wallet["total_trades"]
        mean = wallet["avg_trade_size"]
        m2 = wallet["m2"]
        first_seen = _as_utc(wallet["first_seen_at"])

    # z-score against the wallet's previous trades only, so an outlier can't
    # inflate the standard deviation it is measured against
    z_score = 0.0
    if n_prev >= 2:
        variance = m2 / (n_prev - 1)
        if variance > 0:
            z_score = (size - mean) / math.sqrt(variance)

    # Welford's online algorithm: update mean and M2 (sum of squared deviations)
    # without storing the wallet's past trades
    n = n_prev + 1
    delta = size - mean
    mean += delta / n
    m2 += delta * (size - mean)

    return {
        "trade_size": size,
        "days_since_first_seen": max(0.0, (trade_time - first_seen).total_seconds() / 86_400),
        "total_trades": n,
        "size_z_score": z_score,
        "is_new_wallet": wallet is None,
        "first_seen_at": first_seen,
        "avg_trade_size": mean,
        "m2": m2,
    }
