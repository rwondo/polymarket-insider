from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import get_db
from src.db.models import Anomaly


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def add_anomaly(db, wallet, score):
    db.add(
        Anomaly(
            wallet_address=wallet,
            market_id="0xmarket",
            market_title="Will it rain tomorrow?",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            score=score,
            explanation="test reason",
        )
    )
    db.commit()


def test_root(client):
    assert client.get("/").json()["status"] == "ok"


def test_recent_anomalies(client, db):
    add_anomaly(db, "0xa", 70.0)

    response = client.get("/api/anomalies")
    assert response.status_code == 200
    assert response.json()[0]["market_title"] == "Will it rain tomorrow?"


def test_top_wallets(client, db):
    add_anomaly(db, "0xa", 70.0)
    add_anomaly(db, "0xa", 90.0)
    add_anomaly(db, "0xb", 65.0)

    response = client.get("/api/wallets/top")
    assert response.status_code == 200
    top = response.json()[0]
    assert top == {"wallet": "0xa", "avg_score": 80.0, "flag_count": 2}


def test_limit_is_validated(client):
    assert client.get("/api/anomalies?limit=0").status_code == 422
    assert client.get("/api/anomalies?limit=101").status_code == 422
