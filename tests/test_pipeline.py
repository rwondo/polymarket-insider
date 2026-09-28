import httpx
from conftest import make_trade

from main import process_trade
from src.db.models import Anomaly, Trade, WalletStat
from src.models.anomaly_detector import AnomalyDetector
from src.notifier.webhook import send_alert, send_trade_log


class FixedScoreDetector(AnomalyDetector):
    def __init__(self, score):
        super().__init__()
        self.fixed = score

    def score(self, features):
        return self.fixed, ["test reason"]


def test_process_trade_stores_trade_and_wallet(db):
    result = process_trade(db, make_trade("tx1", size_usd=100.0), AnomalyDetector())

    assert result is not None
    row, anomaly = result
    assert anomaly is None
    assert db.query(Trade).count() == 1
    assert row.wallet_trade_count == 1

    wallet = db.get(WalletStat, "0xwallet1")
    assert wallet.total_trades == 1
    assert wallet.avg_trade_size == 100.0


def test_wallet_stats_accumulate(db):
    detector = AnomalyDetector()
    for i, size in enumerate([100.0, 200.0, 300.0]):
        process_trade(db, make_trade(f"tx{i}", size_usd=size), detector)

    wallet = db.get(WalletStat, "0xwallet1")
    assert wallet.total_trades == 3
    assert wallet.avg_trade_size == 200.0


def test_duplicate_trade_is_ignored(db):
    detector = AnomalyDetector()
    process_trade(db, make_trade("tx1"), detector)

    assert process_trade(db, make_trade("tx1"), detector) is None
    assert db.query(Trade).count() == 1
    assert db.get(WalletStat, "0xwallet1").total_trades == 1


def test_high_score_creates_linked_anomaly(db):
    row, anomaly = process_trade(db, make_trade("tx1"), FixedScoreDetector(75.0))

    assert anomaly is not None
    assert anomaly.trade_id == row.id
    assert anomaly.explanation == "test reason"
    assert db.query(Anomaly).count() == 1


def test_score_below_threshold_creates_no_anomaly(db):
    process_trade(db, make_trade("tx1"), FixedScoreDetector(59.9))
    assert db.query(Anomaly).count() == 0


def test_webhooks_do_nothing_without_url(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("should not post")

    monkeypatch.setattr(httpx, "post", fail)
    alert = {
        "wallet_address": "0xwallet1",
        "market_title": "Will it rain tomorrow?",
        "trade_summary": "BUY Yes $100.00 @ 0.50",
        "score": 75.0,
        "explanation": "test reason",
    }
    assert send_alert(alert, url="") is False
    assert send_trade_log(make_trade(), 10.0, url="") is False
