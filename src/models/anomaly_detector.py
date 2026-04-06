import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self):
        # Isolation Forest is great for multidimensional outliers
        self.model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        self.is_trained = False

    def train_initial_model(self, historical_features_df):
        """Train on a batch of historical trades to establish baselines"""
        if historical_features_df.empty:
            return
            
        features = historical_features_df[['trade_size', 'wallet_age_days', 'total_trades', 'size_z_score']]
        self.model.fit(features)
        self.is_trained = True

    def calculate_score(self, features: dict) -> float:
        """
        Calculate an 'Insider Likelihood Score' from 0-100.
        Heuristics + ML Anomaly Score.
        """
        score = 0.0
        
        # 1. Heuristic: Brand new wallet making massive trade (> $10k)
        if features['is_new_wallet'] and features['trade_size'] > 10000:
            score += 40
            
        # 2. Heuristic: Massive deviation from their norm (z-score > 3)
        if features['size_z_score'] > 3.0:
            score += min(30, features['size_z_score'] * 10)
            
        # 3. ML Scoring (Isolation Forest)
        if self.is_trained:
            # Format explicitly for scikit-learn
            X = np.array([[
                features['trade_size'], 
                features['wallet_age_days'], 
                features['total_trades'], 
                features['size_z_score']
            ]])
            
            # decision_function returns [-0.5, 0.5] roughly. Lower is more anomalous.
            anomaly_score = self.model.decision_function(X)[0]
            
            # Map [-0.2, 0.2] to [0, 30] bonus points
            if anomaly_score < 0:
                ml_penalty = min(30, abs(anomaly_score) * 150)
                score += ml_penalty
                
        # Cap at 100
        return min(100.0, score)

    def generate_explanation(self, features: dict, score: float) -> str:
        reasons = []
        if features['is_new_wallet'] and features['trade_size'] > 10000:
            reasons.append("New wallet with massive initial trade.")
        if features['size_z_score'] > 3.0:
            reasons.append(f"Trade size is {features['size_z_score']:.1f} standard deviations above wallet's average.")
        if score >= 80:
            reasons.append("High statistical anomaly registered by ML model.")
            
        return " | ".join(reasons) if reasons else "Normal trade behavior."