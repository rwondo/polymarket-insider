import logging
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime

from src.config import settings
from src.db.database import SessionLocal, Base, engine
from src.db.models import Trade, WalletStat, Anomaly
from src.ingestion.polygon_client import PolymarketClient
from src.features.feature_engineer import FeatureEngineer
from src.models.anomaly_detector import AnomalyDetector
from src.notifier.webhook import send_alert, send_trade_log

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_queue(queue: asyncio.Queue, db: Session, feature_eng: FeatureEngineer, detector: AnomalyDetector):
    """Background worker that continuously pulls trades from the pipeline queue and saves them"""
    logger.info("Started Queue Processor Worker.")
    
    while True:
        trade_data = await queue.get()
        try:
            logger.info(f"New Trade Detected: {trade_data['wallet_address']} | ${trade_data['size_usd']:.2f}")
            
            # Use synchronous SQLAlchemy since this worker runs insulated from the WebSocket ingestion
            wallet_stat = db.query(WalletStat).filter(WalletStat.wallet_address == trade_data['wallet_address']).first()
            current_stats_dict = None
            if wallet_stat:
                current_stats_dict = {
                    "first_trade_at": wallet_stat.first_trade_at,
                    "total_trades": wallet_stat.total_trades,
                    "avg_trade_size": wallet_stat.avg_trade_size,
                    "market_entropy": wallet_stat.market_entropy,
                    "m2": wallet_stat.m2
                }
                
            features = feature_eng.process_new_trade(trade_data, current_stats_dict)
            score = detector.calculate_score(features)
            
            # Send all trades log
            send_trade_log(trade_data, score)
            
            new_trade = Trade(
                transaction_hash=trade_data['transaction_hash'],
                wallet_address=trade_data['wallet_address'],
                market_id=trade_data['market_id'],
                outcome=trade_data['outcome'],
                size_usd=trade_data['size_usd'],
                price=trade_data['price']
            )
            db.add(new_trade)
            
            if wallet_stat:
                wallet_stat.total_trades = features['total_trades']
                wallet_stat.avg_trade_size = features['avg_trade_size']
                wallet_stat.m2 = features['m2']
            else:
                new_wallet = WalletStat(
                    wallet_address=trade_data['wallet_address'],
                    first_trade_at=datetime.utcnow(),
                    total_trades=1,
                    avg_trade_size=features['avg_trade_size'],
                    m2=0.0
                )
                db.add(new_wallet)
                
            if score > settings.ANOMALY_THRESHOLD:
                explanation = detector.generate_explanation(features, score)
                logger.warning(f"🚨 ANOMALY DETECTED! Score: {score:.1f} | Reason: {explanation}")
                
                anomaly = Anomaly(
                    wallet_address=trade_data['wallet_address'],
                    market_id=trade_data['market_id'],
                    score=score,
                    explanation=explanation
                )
                db.add(anomaly)
                db.commit()
                
                send_alert({
                    "wallet_address": trade_data['wallet_address'],
                    "market_id": trade_data['market_id'],
                    "score": score,
                    "trade_size": trade_data['size_usd'],
                    "explanation": explanation
                })
            else:
                db.commit()
                
        except Exception as e:
            logger.error(f"Error processing trade from queue: {e}")
            db.rollback()
        finally:
            queue.task_done()

async def periodic_model_retraining(db: Session, detector: AnomalyDetector):
    """Awakes periodically to pull historical DB data and retrain the IsolationForest."""
    while True:
        try:
            logger.info("Initializing Periodic Model Retraining sequence.")
            # For brevity, in prod query the last 7 days of raw Trade features via pandas
            # import pandas as pd
            # df = pd.read_sql("SELECT * FROM ...", con=db.bind)
            # detector.train_initial_model(df)
        except Exception as e:
            logger.error(f"Failed to retrain ML model: {e}")
        
        await asyncio.sleep(3600)  # Retrain every hour

async def start_processes():
    logger.info("Starting Polymarket Insider Detection System...")
    
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    queue = asyncio.Queue()
    client = PolymarketClient(queue)
    feature_eng = FeatureEngineer(db)
    detector = AnomalyDetector()
    
    # 1. Start WebSocket Listener
    ingestion_task = asyncio.create_task(client.listen_for_trades())
    # 2. Start synchronous DB Processing Queue
    processor_task = asyncio.create_task(process_queue(queue, db, feature_eng, detector))
    # 3. Start hourly background ML retraining
    retrain_task = asyncio.create_task(periodic_model_retraining(db, detector))
    
    await asyncio.gather(ingestion_task, processor_task, retrain_task)

if __name__ == "__main__":
    try:
        asyncio.run(start_processes())
    except KeyboardInterrupt:
        logger.info("Gracefully shutting down...")