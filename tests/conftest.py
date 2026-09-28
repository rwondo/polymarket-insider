import os

# Point settings at an in-memory database and default values before any src module loads
os.environ.update(
    DATABASE_URL="sqlite://",
    WEBHOOK_URL="",
    ALL_TRADES_WEBHOOK_URL="",
    ANOMALY_THRESHOLD="60",
    LARGE_TRADE_USD="10000",
)

from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import src.db.models  # noqa: E402, F401  (registers the tables)
from src.db.database import Base  # noqa: E402


@pytest.fixture
def db():
    # StaticPool keeps one connection, so the in-memory database is shared across threads
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def make_trade(key="tx1", wallet="0xwallet1", size_usd=100.0, ts=None, **overrides):
    trade = {
        "trade_key": key,
        "transaction_hash": key,
        "wallet_address": wallet,
        "market_id": "0xmarket",
        "market_title": "Will it rain tomorrow?",
        "outcome": "Yes",
        "side": "BUY",
        "price": 0.5,
        "size_usd": size_usd,
        "timestamp": ts or datetime(2026, 1, 1, tzinfo=UTC),
    }
    trade.update(overrides)
    return trade
