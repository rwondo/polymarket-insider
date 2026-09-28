import numpy as np
from sklearn.ensemble import IsolationForest

from src.config import settings
from src.features.feature_engineer import ML_FEATURES

# Score components (0-100 in total)
NEW_WALLET_POINTS = 40  # first trade we see from a wallet is above LARGE_TRADE_USD
Z_SCORE_CUTOFF = 3.0
Z_SCORE_POINTS = 30  # trade is more than 3 std devs above the wallet's average
ML_MAX_POINTS = 30  # Isolation Forest says outlier
ML_POINTS_PER_UNIT = 150  # a decision score of -0.2 or lower earns the full 30 points


def feature_vector(features: dict) -> list[float]:
    return [float(features[name]) for name in ML_FEATURES]


class AnomalyDetector:
    def __init__(self, large_trade_usd: float | None = None):
        self.large_trade_usd = large_trade_usd or settings.LARGE_TRADE_USD
        self.model: IsolationForest | None = None
        self.trained_on = 0

    @property
    def is_trained(self) -> bool:
        return self.model is not None

    def train(self, rows) -> None:
        """Fit a fresh Isolation Forest on rows of ML_FEATURES, then swap it in."""
        X = np.asarray(rows, dtype=float)
        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        model.fit(X)
        # One assignment, so scoring never sees a half-trained model
        self.model = model
        self.trained_on = len(X)

    def score(self, features: dict) -> tuple[float, list[str]]:
        """Return an unusualness score from 0 to 100 and the reasons behind it."""
        score = 0.0
        reasons = []

        if features["is_new_wallet"] and features["trade_size"] > self.large_trade_usd:
            score += NEW_WALLET_POINTS
            reasons.append(f"First trade seen from this wallet is ${features['trade_size']:,.0f}.")

        z_score = features["size_z_score"]
        if z_score > Z_SCORE_CUTOFF:
            score += Z_SCORE_POINTS
            reasons.append(
                f"Trade is {z_score:.1f} standard deviations above this wallet's average size."
            )

        model = self.model
        if model is not None:
            # decision_function < 0: the forest isolates this trade in fewer splits than
            # the contamination cutoff allows, i.e. it looks like an outlier
            decision = model.decision_function(np.array([feature_vector(features)]))[0]
            if decision < 0:
                score += min(ML_MAX_POINTS, -decision * ML_POINTS_PER_UNIT)
                reasons.append(f"Isolation Forest outlier (decision score {decision:.3f}).")

        return min(100.0, score), reasons
