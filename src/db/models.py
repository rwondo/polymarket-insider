from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from src.db.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    trade_key = Column(String, unique=True, index=True, nullable=False)
    transaction_hash = Column(String, index=True)
    wallet_address = Column(String, index=True)
    market_id = Column(String, index=True)
    market_title = Column(String)
    outcome = Column(String)
    side = Column(String)  # BUY/SELL
    price = Column(Float)
    size_usd = Column(Float)
    timestamp = Column(DateTime(timezone=True), index=True)

    # Features at the time of the trade; the Isolation Forest is retrained on these
    days_since_first_seen = Column(Float)
    wallet_trade_count = Column(Integer)
    size_z_score = Column(Float)
    score = Column(Float)


class WalletStat(Base):
    """Running stats per wallet, updated with Welford's algorithm."""

    __tablename__ = "wallet_stats"

    wallet_address = Column(String, primary_key=True)
    first_seen_at = Column(DateTime(timezone=True))
    total_trades = Column(Integer, default=0)
    avg_trade_size = Column(Float, default=0.0)
    m2 = Column(Float, default=0.0)  # sum of squared deviations from the mean
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), index=True)
    wallet_address = Column(String, index=True)
    market_id = Column(String, index=True)
    market_title = Column(String)
    timestamp = Column(DateTime(timezone=True), index=True)
    score = Column(Float)
    explanation = Column(String)
