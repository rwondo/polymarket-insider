import asyncio
from datetime import UTC, datetime

import pytest

from src.ingestion.trade_feed import TradeFeed, parse_trade


def api_row(tx, ts, size=10, price=0.25, wallet="0xwallet1"):
    """Shape of one row from GET https://data-api.polymarket.com/trades (synthetic values)."""
    return {
        "transactionHash": tx,
        "asset": "123",
        "proxyWallet": wallet,
        "side": "BUY",
        "size": size,
        "price": price,
        "timestamp": ts,
        "conditionId": "0xmarket",
        "title": "Will it rain tomorrow?",
        "outcome": "Yes",
    }


def feed():
    return TradeFeed(asyncio.Queue(), url="http://example.invalid", interval=1)


def test_parse_trade_converts_shares_to_dollars():
    trade = parse_trade(api_row("0xabc", 1_790_000_000, size=40, price=0.25))

    assert trade["size_usd"] == pytest.approx(10.0)
    assert trade["price"] == 0.25
    assert trade["timestamp"] == datetime.fromtimestamp(1_790_000_000, tz=UTC)
    assert trade["market_title"] == "Will it rain tomorrow?"


def test_new_trades_are_deduplicated_and_ordered_oldest_first():
    f = feed()
    # The API returns newest first
    first = f.new_trades([api_row("0x3", 300), api_row("0x2", 200), api_row("0x1", 100)])
    assert [t["transaction_hash"] for t in first] == ["0x1", "0x2", "0x3"]

    second = f.new_trades([api_row("0x4", 400), api_row("0x3", 300)])
    assert [t["transaction_hash"] for t in second] == ["0x4"]
    assert f.gaps == 0


def test_batch_without_overlap_counts_as_possible_gap():
    f = feed()
    f.new_trades([api_row("0x1", 100)])
    f.new_trades([api_row("0x9", 900)])
    assert f.gaps == 1


def test_malformed_rows_are_skipped():
    bad = api_row("0xbad", 100)
    del bad["price"]
    trades = feed().new_trades([bad, api_row("0xgood", 200)])
    assert [t["transaction_hash"] for t in trades] == ["0xgood"]
