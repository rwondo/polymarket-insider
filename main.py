import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.db.database import Base, SessionLocal, engine
from src.db.models import Anomaly, Trade, WalletStat
from src.features.feature_engineer import compute_features
from src.ingestion.trade_feed import TradeFeed
from src.models.anomaly_detector import AnomalyDetector
from src.notifier.webhook import send_alert, send_trade_log, trade_summary

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TRAINING_WINDOW = 50_000  # most recent trades used to retrain the Isolation Forest
FIRST_TRAINING_CHECK_SECONDS = 60
PROGRESS_EVERY = 1_000  # log a summary line every N trades


def process_trade(
    db: Session, trade: dict, detector: AnomalyDetector
) -> tuple[Trade, Anomaly | None] | None:
    """Score one trade, update the wallet's running stats and store everything.

    Returns None if the trade is already stored (e.g. re-polled after a restart).
    """
    if db.scalar(select(Trade.id).where(Trade.trade_key == trade["trade_key"])):
        return None

    wallet = db.get(WalletStat, trade["wallet_address"])
    previous = None
    if wallet:
        previous = {
            "first_seen_at": wallet.first_seen_at,
            "total_trades": wallet.total_trades,
            "avg_trade_size": wallet.avg_trade_size,
            "m2": wallet.m2,
        }

    features = compute_features(trade, previous)
    score, reasons = detector.score(features)

    row = Trade(
        trade_key=trade["trade_key"],
        transaction_hash=trade["transaction_hash"],
        wallet_address=trade["wallet_address"],
        market_id=trade["market_id"],
        market_title=trade["market_title"],
        outcome=trade["outcome"],
        side=trade["side"],
        price=trade["price"],
        size_usd=trade["size_usd"],
        timestamp=trade["timestamp"],
        days_since_first_seen=features["days_since_first_seen"],
        wallet_trade_count=features["total_trades"],
        size_z_score=features["size_z_score"],
        score=score,
    )
    db.add(row)

    if wallet is None:
        wallet = WalletStat(
            wallet_address=trade["wallet_address"], first_seen_at=features["first_seen_at"]
        )
        db.add(wallet)
    wallet.total_trades = features["total_trades"]
    wallet.avg_trade_size = features["avg_trade_size"]
    wallet.m2 = features["m2"]

    anomaly = None
    if score >= settings.ANOMALY_THRESHOLD:
        db.flush()  # assigns row.id
        anomaly = Anomaly(
            trade_id=row.id,
            wallet_address=trade["wallet_address"],
            market_id=trade["market_id"],
            market_title=trade["market_title"],
            timestamp=trade["timestamp"],
            score=score,
            explanation=" | ".join(reasons),
        )
        db.add(anomaly)

    db.commit()
    return row, anomaly


async def process_queue(
    queue: asyncio.Queue, detector: AnomalyDetector, feed: TradeFeed | None = None
) -> None:
    """Consume trades from the queue: score, store and alert."""
    logger.info("Started trade processor")
    db = SessionLocal()
    processed = flagged = 0

    while True:
        trade = await queue.get()
        try:
            result = process_trade(db, trade, detector)
            if result is None:
                continue
            row, anomaly = result
            processed += 1

            if settings.ALL_TRADES_WEBHOOK_URL:
                await asyncio.to_thread(send_trade_log, trade, row.score)

            if anomaly:
                flagged += 1
                logger.warning(
                    "Anomaly: score %.1f | %s | %s | %s",
                    anomaly.score,
                    trade_summary(trade),
                    trade["market_title"],
                    anomaly.explanation,
                )
                alert = {
                    "wallet_address": anomaly.wallet_address,
                    "market_title": anomaly.market_title or "",
                    "trade_summary": trade_summary(trade),
                    "score": anomaly.score,
                    "explanation": anomaly.explanation,
                }
                await asyncio.to_thread(send_alert, alert)

            if processed % PROGRESS_EVERY == 0:
                logger.info(
                    "Processed %d trades | flagged %d | queue %d | gaps %d | model trained on %d",
                    processed,
                    flagged,
                    queue.qsize(),
                    feed.gaps if feed else 0,
                    detector.trained_on,
                )
        except Exception:
            logger.exception("Failed to process trade %s", trade.get("trade_key"))
            db.rollback()
        finally:
            queue.task_done()


def load_training_rows(limit: int = TRAINING_WINDOW) -> list:
    # Column order must match ML_FEATURES in src/features/feature_engineer.py
    with SessionLocal() as db:
        return db.execute(
            select(
                Trade.size_usd,
                Trade.days_since_first_seen,
                Trade.wallet_trade_count,
                Trade.size_z_score,
            )
            .order_by(Trade.id.desc())
            .limit(limit)
        ).all()


async def retrain_periodically(detector: AnomalyDetector) -> None:
    """Refit the Isolation Forest on recent trades, first as soon as there are enough."""
    while True:
        try:
            rows = await asyncio.to_thread(load_training_rows)
            if len(rows) >= settings.MIN_TRAINING_TRADES:
                await asyncio.to_thread(detector.train, rows)
                logger.info("Trained Isolation Forest on %d trades", len(rows))
            else:
                logger.info(
                    "Waiting for %d trades before training the model (have %d)",
                    settings.MIN_TRAINING_TRADES,
                    len(rows),
                )
        except Exception:
            logger.exception("Retraining failed")

        if detector.is_trained:
            await asyncio.sleep(settings.RETRAIN_INTERVAL_SECONDS)
        else:
            await asyncio.sleep(FIRST_TRAINING_CHECK_SECONDS)


async def run() -> None:
    logger.info("Starting Polymarket trade monitor")
    Base.metadata.create_all(bind=engine)

    queue: asyncio.Queue = asyncio.Queue()
    detector = AnomalyDetector()
    feed = TradeFeed(queue)

    await asyncio.gather(
        feed.run(),
        process_queue(queue, detector, feed),
        retrain_periodically(detector),
    )


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Shutting down")
