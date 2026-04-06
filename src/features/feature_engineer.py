import pandas as pd
import numpy as np
from datetime import datetime
import math

class FeatureEngineer:
    def __init__(self, db_session):
        self.db = db_session

    def process_new_trade(self, trade_data: dict, current_wallet_stats: dict):
        """
        Calculate ML features using Welford's Algorithm for running variance.
        """
        size = trade_data['size_usd']
        wallet = trade_data['wallet_address']
        
        # 1. Wallet Features
        is_new_wallet = current_wallet_stats is None
        total_trades = 1 if is_new_wallet else current_wallet_stats['total_trades'] + 1
        
        if is_new_wallet:
            avg_size = size
            new_m2 = 0.0
            z_score = 0.0  # Can't calculate z-score on first trade
            wallet_age_days = 0
        else:
            prev_avg = current_wallet_stats['avg_trade_size']
            prev_m2 = current_wallet_stats.get('m2', 0.0)
            
            # Welford's Online Algorithm for Variance
            delta = size - prev_avg
            avg_size = prev_avg + delta / total_trades
            delta2 = size - avg_size
            new_m2 = prev_m2 + delta * delta2
            
            # Calculate Standard Deviation (Sample Variance)
            variance = new_m2 / (total_trades - 1) if total_trades > 1 else 0
            
            # Prevent zero-division for std_dev in very fresh/stable wallets
            if variance > 0:
                std_dev = math.sqrt(variance)
            else:
                std_dev = (prev_avg / 2) if prev_avg > 0 else 1.0
                
            z_score = delta / std_dev if std_dev > 0 else 0.0
            
            first_trade = current_wallet_stats['first_trade_at']
            wallet_age_days = (datetime.utcnow() - first_trade.replace(tzinfo=None)).days

        # 2. Trade/Market Features
        
        features = {
            "trade_size": size,
            "wallet_age_days": wallet_age_days,
            "total_trades": total_trades,
            "avg_trade_size": avg_size,
            "m2": new_m2,
            "size_z_score": z_score,
            "is_new_wallet": int(is_new_wallet)
        }
        
        return features