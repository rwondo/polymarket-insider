"""Summarise a monitoring run from the database.

Trades with a timestamp before --since came from the startup backfill; trades after it
were picked up live, so only those have a meaningful detection delay.

Usage:
    uv run python scripts/run_stats.py --since "2026-09-28 20:24:31"
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings  # noqa: E402
from src.db.database import SessionLocal  # noqa: E402
from src.db.models import Anomaly, Trade  # noqa: E402


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def pct(values, q) -> float:
    return float(np.percentile(values, q)) if len(values) else float("nan")


def short(wallet: str) -> str:
    return f"{wallet[:6]}…{wallet[-4:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, help="run start, UTC, 'YYYY-MM-DD HH:MM:SS'")
    since = as_utc(datetime.fromisoformat(parser.parse_args().since))

    with SessionLocal() as db:
        trades = db.execute(
            select(Trade.timestamp, Trade.received_at, Trade.score, Trade.wallet_address)
        ).all()
        anomalies = db.scalars(select(Anomaly).order_by(Anomaly.score.desc())).all()

    backfill = [t for t in trades if as_utc(t.timestamp) < since]
    live = [t for t in trades if as_utc(t.timestamp) >= since]
    delays = [(as_utc(t.received_at) - as_utc(t.timestamp)).total_seconds() / 60 for t in live]
    scores = [t.score for t in live]

    wallets = len({t.wallet_address for t in trades})
    print(f"Trades stored:          {len(trades):,} ({wallets:,} wallets)")
    if backfill:
        oldest = min(as_utc(t.timestamp) for t in backfill)
        hours = (since - oldest).total_seconds() / 3600
        print(f"  from startup backfill {len(backfill):,} (covering {hours:.1f} h before start)")
    print(f"  picked up live        {len(live):,}")
    if live:
        print(
            f"Detection delay (min):  median {pct(delays, 50):.1f}, "
            f"p90 {pct(delays, 90):.1f}, max {max(delays):.1f}"
        )
        print(
            f"Live scores:            p50 {pct(scores, 50):.1f}, p90 {pct(scores, 90):.1f}, "
            f"p99 {pct(scores, 99):.1f}, max {max(scores):.1f}"
        )
        print(f"  score > 0             {sum(s > 0 for s in scores) / len(scores):.1%}")
    print(f"Flagged (score >= {settings.ANOMALY_THRESHOLD:.0f}):  {len(anomalies)}")
    for a in anomalies[:10]:
        print(f"  {a.score:5.1f}  {short(a.wallet_address)}  {a.market_title[:60]}")
        print(f"         {a.explanation}")


if __name__ == "__main__":
    main()
