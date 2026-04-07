import requests
import logging
from src.config import settings

logger = logging.getLogger(__name__)

def send_alert(anomaly_data: dict):
    """
    Send an alert to Discord or Telegram webhook for anomalous trades.
    """
    url = settings.WEBHOOK_URL
    if not url:
        logger.warning("No WEBHOOK_URL configured. Skipping alert.")
        return

    # Assuming Discord formatting for this example
    payload = {
        "content": "🚨 **Polymarket Insider Alert** 🚨",
        "embeds": [
            {
                "title": "Abnormal Trade Detected",
                "color": 16711680, # Red
                "fields": [
                    {"name": "Wallet", "value": f"`{anomaly_data['wallet_address']}`", "inline": False},
                    {"name": "Market ID", "value": f"`{anomaly_data['market_id']}`", "inline": False},
                    {"name": "Score", "value": f"**{anomaly_data['score']:.1f}/100**", "inline": True},
                    {"name": "Trade Size", "value": f"${anomaly_data['trade_size']:,.2f}", "inline": True},
                    {"name": "Explanation", "value": anomaly_data['explanation'], "inline": False},
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"Alert sent for wallet {anomaly_data['wallet_address']}")
    except Exception as e:
        logger.error(f"Failed to send webhook alert: {e}")

def send_trade_log(trade_data: dict, score: float):
    """
    Log every trade to a separate Discord webhook.
    """
    url = settings.ALL_TRADES_WEBHOOK_URL
    if not url:
        return
        
    payload = {
        "content": "📊 **Trade Logged**",
        "embeds": [
            {
                "title": "Trade Information",
                "color": 3447003, # Blue
                "fields": [
                    {"name": "Wallet", "value": f"`{trade_data['wallet_address']}`", "inline": False},
                    {"name": "Market ID", "value": f"`{trade_data['market_id']}`", "inline": False},
                    {"name": "Score", "value": f"{score:.1f}/100", "inline": True},
                    {"name": "Trade Size", "value": f"${trade_data['size_usd']:,.2f}", "inline": True},
                    {"name": "Outcome", "value": str(trade_data.get('outcome', 'N/A')), "inline": True},
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send all trades webhook log: {e}")