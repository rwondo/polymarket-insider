import asyncio
import logging
from collections import deque
from datetime import UTC, datetime

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # the API's maximum page size
SEEN_KEYS_LIMIT = 20_000  # must exceed backfill + one page so consecutive batches can overlap


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

    def __init__(
        self,
        queue: asyncio.Queue,
        url: str | None = None,
        interval: float | None = None,
        min_usd: float | None = None,
        backfill: int | None = None,
    ):
        self.queue = queue
        self.url = url or settings.TRADES_API_URL
        self.interval = interval or settings.POLL_INTERVAL_SECONDS
        self.min_usd = settings.MIN_TRADE_USD if min_usd is None else min_usd
        self.backfill_trades = settings.BACKFILL_TRADES if backfill is None else backfill
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
            # Backfill pages can overlap if the API cache refreshes while paging
            if trade["trade_key"] in self._seen:
                continue
            self._remember(trade["trade_key"])
            trades.append(trade)
        return trades

    async def fetch(self, client: httpx.AsyncClient, offset: int = 0) -> list[dict]:
        """One page of the newest trades worth at least min_usd (the API's cash filter)."""
        params = {
            "limit": BATCH_SIZE,
            "offset": offset,
            "filterType": "CASH",
            "filterAmount": self.min_usd,
        }
        response = await client.get(self.url, params=params)
        response.raise_for_status()
        return response.json()

    async def backfill(self, client: httpx.AsyncClient) -> None:
        """Load recent history so wallet stats and the model have data from the start."""
        rows: list[dict] = []
        for offset in range(0, self.backfill_trades, BATCH_SIZE):
            page = await self.fetch(client, offset)
            rows.extend(page)
            if len(page) < BATCH_SIZE:
                break
        trades = self.new_trades(rows)
        for trade in trades:
            await self.queue.put(trade)
        logger.info("Backfilled %d trades of $%.0f or more", len(trades), self.min_usd)

    async def run(self) -> None:
        logger.info(
            "Polling %s every %.0fs for trades of $%.0f or more",
            self.url,
            self.interval,
            self.min_usd,
        )
        async with httpx.AsyncClient(timeout=15) as client:
            if self.backfill_trades > 0:
                try:
                    await self.backfill(client)
                except (httpx.HTTPError, ValueError) as e:
                    logger.error("Backfill failed, continuing with live polling: %s", e)

            while True:
                try:
                    for trade in self.new_trades(await self.fetch(client)):
                        await self.queue.put(trade)
                except (httpx.HTTPError, ValueError) as e:
                    logger.error("Trade feed request failed: %s", e)
                await asyncio.sleep(self.interval)
