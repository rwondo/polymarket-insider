from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from src.db.database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    transaction_hash = Column(String, unique=True, index=True)
    wallet_address = Column(String, index=True)
    market_id = Column(String, index=True)
    outcome = Column(String) # YES/NO
    size_usd = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime(timezone=True), default=func.now())

class WalletStat(Base):
    __tablename__ = "wallet_stats"

    wallet_address = Column(String, primary_key=True, index=True)
    first_trade_at = Column(DateTime(timezone=True))
    total_trades = Column(Integer, default=0)
    avg_trade_size = Column(Float, default=0.0)
    m2 = Column(Float, default=0.0)
    market_entropy = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String, index=True)
    market_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    score = Column(Float)
    explanation = Column(String)
    trade_id = Column(Integer, ForeignKey("trades.id"))