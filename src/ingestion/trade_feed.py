import asyncio
import logging
from collections import deque
from datetime import UTC, datetime

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # the API's page size; ~15s of trades at typical volume
SEEN_KEYS_LIMIT = 5_000  # must be larger than BATCH_SIZE so consecutive batches can overlap


def trade_key(row: dict) -> str:
    return f"{row['transactionHash']}:{row['asset']}:{row['proxyWallet']}:{row['side']}"


def parse_trade(row: dict) -> dict:
    """Convert one API row into the pipeline's trade dict."""
    size = float(row["size"])  # number of outcome shares
    price = float(row["price"])  # 0..1, the implied probability
    return {
        "trade_key": trade_key(row),
        "transaction_hash": row["transactionHash"],
        "wallet_address": row["proxyWallet"],
        "market_id": row["conditionId"],
        "market_title": row.get("title", ""),
        "outcome": row.get("outcome", ""),
        "side": row.get("side", ""),
        "price": price,
        "size_usd": size * price,
        "timestamp": datetime.fromtimestamp(int(row["timestamp"]), tz=UTC),
    }


class TradeFeed:
    """Polls Polymarket's public trades API and queues the trades it hasn't seen yet."""

    def __init__(self, queue: asyncio.Queue, url: str | None = None, interval: float | None = None):
        self.queue = queue
        self.url = url or settings.TRADES_API_URL
        self.interval = interval or settings.POLL_INTERVAL_SECONDS
        self._seen: set[str] = set()
        self._seen_order: deque[str] = deque()
        self.gaps = 0

    def _remember(self, key: str) -> None:
        self._seen.add(key)
        self._seen_order.append(key)
        if len(self._seen_order) > SEEN_KEYS_LIMIT:
            self._seen.discard(self._seen_order.popleft())

    def new_trades(self, rows: list[dict]) -> list[dict]:
        """Return unseen trades from one API batch, oldest first."""
        fresh = [r for r in rows if trade_key(r) not in self._seen]
        # If nothing in this batch was seen before, trades may have slipped between polls
        if self._seen and rows and len(fresh) == len(rows):
            self.gaps += 1
            logger.warning("Possible gap: batch has no overlap with the previous one")

        trades = []
        for row in sorted(fresh, key=lambda r: r["timestamp"]):
            try:
                trade = parse_trade(row)
            except (KeyError, TypeError, ValueError):
                logger.debug("Skipping malformed trade row: %s", row)
                continue
            self._remember(trade["trade_key"])
            trades.append(trade)
        return trades

    async def run(self) -> None:
        logger.info("Polling %s every %.0fs", self.url, self.interval)
        async with httpx.AsyncClient(timeout=15) as client:
            while True:
                try:
                    response = await client.get(self.url, params={"limit": BATCH_SIZE})
                    response.raise_for_status()
                    for trade in self.new_trades(response.json()):
                        await self.queue.put(trade)
                except (httpx.HTTPError, ValueError) as e:
                    logger.error("Trade feed request failed: %s", e)
                await asyncio.sleep(self.interval)
