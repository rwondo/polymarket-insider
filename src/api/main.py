from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from src.db.database import get_db, engine, Base
from src.db.models import Anomaly, Trade

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polymarket Insider Detection API")

class AnomalyResponse(BaseModel):
    wallet_address: str
    market_id: str
    score: float
    explanation: str

    class Config:
        from_attributes = True

@app.get("/")
def read_root():
    return {"status": "System Online", "service": "Polymarket Insider Detection"}

@app.get("/api/anomalies", response_model=List[AnomalyResponse])
def get_recent_anomalies(limit: int = 10, db: Session = Depends(get_db)):
    anomalies = db.query(Anomaly).order_by(Anomaly.timestamp.desc()).limit(limit).all()
    return anomalies

@app.get("/api/wallets/top")
def get_top_flagged_wallets(db: Session = Depends(get_db)):
    """Returns wallets with the highest average anomaly scores."""
    from sqlalchemy.sql import func
    
    results = db.query(
        Anomaly.wallet_address, 
        func.avg(Anomaly.score).label('avg_score'),
        func.count(Anomaly.id).label('flag_count')
    ).group_by(Anomaly.wallet_address)\
     .having(func.count(Anomaly.id) > 0)\
     .order_by(func.avg(Anomaly.score).desc())\
     .limit(10).all()
     
    return [{"wallet": r[0], "avg_score": r[1], "flag_count": r[2]} for r in results]