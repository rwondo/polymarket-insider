import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


def _post(url: str, payload: dict) -> bool:
    try:
        httpx.post(url, json=payload, timeout=TIMEOUT_SECONDS).raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.error("Webhook post failed: %s", e)
        return False


def send_alert(anomaly: dict, url: str | None = None) -> bool:
    """Post a flagged trade to the Discord alert webhook."""
    url = settings.WEBHOOK_URL if url is None else url
    if not url:
        logger.info("No WEBHOOK_URL configured, skipping alert")
        return False

    payload = {
        "content": "**Unusual Polymarket trade**",
        "embeds": [
            {
                "title": anomaly["market_title"][:256] or "Unknown market",
                "color": 16711680,  # red
                "fields": [
                    {"name": "Wallet", "value": f"`{anomaly['wallet_address']}`"},
                    {"name": "Trade", "value": anomaly["trade_summary"], "inline": True},
                    {"name": "Score", "value": f"**{anomaly['score']:.1f}/100**", "inline": True},
                    {"name": "Reasons", "value": anomaly["explanation"][:1024]},
                ],
            }
        ],
    }
    return _post(url, payload)


def send_trade_log(trade: dict, score: float, url: str | None = None) -> bool:
    """Post every trade to a second webhook (optional, noisy at Polymarket's volume)."""
    url = settings.ALL_TRADES_WEBHOOK_URL if url is None else url
    if not url:
        return False

    payload = {
        "embeds": [
            {
                "title": trade["market_title"][:256] or "Unknown market",
                "color": 3447003,  # blue
                "fields": [
                    {"name": "Wallet", "value": f"`{trade['wallet_address']}`"},
                    {"name": "Trade", "value": trade_summary(trade), "inline": True},
                    {"name": "Score", "value": f"{score:.1f}/100", "inline": True},
                ],
            }
        ],
    }
    return _post(url, payload)


def trade_summary(trade: dict) -> str:
    return f"{trade['side']} {trade['outcome']} ${trade['size_usd']:,.2f} @ {trade['price']:.2f}"
