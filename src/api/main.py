from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.database import Base, engine, get_db
from src.db.models import Anomaly

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polymarket Insider API")

DbSession = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wallet_address: str
    market_id: str
    market_title: str | None
    timestamp: datetime
    score: float
    explanation: str


class FlaggedWallet(BaseModel):
    wallet: str
    avg_score: float
    flag_count: int


@app.get("/")
def read_root():
    return {"status": "ok", "service": "polymarket-insider"}


@app.get("/api/anomalies", response_model=list[AnomalyResponse])
def get_recent_anomalies(db: DbSession, limit: Limit = 10):
    """Most recent flagged trades."""
    return db.scalars(select(Anomaly).order_by(Anomaly.timestamp.desc()).limit(limit)).all()


@app.get("/api/wallets/top", response_model=list[FlaggedWallet])
def get_top_flagged_wallets(db: DbSession, limit: Limit = 10):
    """Wallets with the highest average anomaly score."""
    avg_score = func.avg(Anomaly.score)
    rows = db.execute(
        select(Anomaly.wallet_address, avg_score, func.count(Anomaly.id))
        .group_by(Anomaly.wallet_address)
        .order_by(avg_score.desc())
        .limit(limit)
    ).all()
    return [FlaggedWallet(wallet=w, avg_score=s, flag_count=c) for w, s, c in rows]
