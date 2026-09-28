# Polymarket Insider Detection System

A production-ready, quantitative system that monitors Polymarket on Polygon in real-time to detect insider trading behavior, information asymmetry, and coordinated wallet attacks using advanced machine learning and statistical analysis.

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** ← Start here! Complete checklist to get running.
- **[API_KEYS_SETUP.md](API_KEYS_SETUP.md)** — Step-by-step guide to obtain all required API keys (Alchemy, Discord, Database).
- **[README.md](README.md)** — This file. Architecture & technical details.

## Project Structure

```
├── docker-compose.yml           # Local Postgres/Redis infrastructure
├── main.py                      # Orchestrator script (Background worker)
├── requirements.txt             # Python dependencies
├── .env.example                 # Template for environment variables
└── src/
    ├── api/                     # FastAPI endpoints (Dashboard layer)
    │   └── main.py
    ├── config.py                # Pydantic Settings
    ├── db/                      # SQLAlchemy ORM and config
    │   ├── database.py
    │   └── models.py
    ├── features/                # State management and feature calculations
    │   └── feature_engineer.py
    ├── ingestion/               # Real-time Web3 polling/WebSocket
    │   └── polygon_client.py
    ├── models/                  # ML/Heuristic anomaly detection (IsolationForest)
    │   └── anomaly_detector.py
    └── notifier/                # Discord/Telegram webhooks
        └── webhook.py
```

## ⚡ Quick Start (30 seconds)

**Not ready yet?** Follow [API_KEYS_SETUP.md](API_KEYS_SETUP.md) first to get your Alchemy & Discord keys.

```powershell
# 1. Start database (background)
docker-compose up -d

# 2. Create and fill .env (copy .env.example and add your keys)
# POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
# POLYGON_WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
# WEBHOOK_URL=https://discord.com/api/webhooks/...

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the system (opens real-time monitoring)
python main.py
```

**Expected logs:**
```
2026-04-06 ... INFO - Starting Polymarket Insider Detection System...
2026-04-06 ... INFO - Listening for trades on ... via WSS...
2026-04-06 ... INFO - Started Queue Processor Worker.
```

**In a new terminal, view API docs:**
```powershell
uvicorn src.api.main:app --reload
# Browse to http://127.0.0.1:8000/docs
```

✅ **You're live!** The system is now monitoring Polymarket and sending Discord alerts.

## Deployment

### Strategy
For production deployments, separate the components:

1. 🚀 Production Deployment

Once you've tested locally for 30+ minutes without errors, deploy to production:

### Via Docker Compose (Recommended)

1. **Spin up a server** (EC2, DigitalOcean, Railway, Render, etc.)
2. **Install Docker & Docker Compose**
3. **Copy your `.env` file securely to the server** (NOT via git!)
4. **Run on the server:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
5. **Verify everything is healthy:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   # db (healthy) | worker (running) | api (running)
   ```

### Architecture (Production)

```
┌─────────────────────────────────────────┐
│      Alchemy Polygon WebSocket (WSS)   │
└────────────────────┬────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  Async WebSocket Loop  │  (Worker)
        │  (polygon_client.py)   │
        └────────────┬───────────┘
                     │ (Raw Events)
                     ▼
        ┌────────────────────────┐
        │  asyncio.Queue         │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  Feature Engineering   │  (Worker)
        │  + ML Scoring          │
        │  (main.py)             │
        └────────────┬───────────┘
                     │ (Anomalies)
                     ▼
        ┌────────────────────────┐
        │  PostgreSQL Database   │
        │  (Trades, Wallets,     │  (Managed Service)
        │   Anomalies)           │
        └────────────┬───────────┘
                     │
        ┌────────────┴──────────┐
        ▼                       ▼
    Discord Alerts       REST API (FastAPI)
    (Consumer Devices)    (Dashboard/Queries)
```

### Key Production Improvements Implemented:
✅ **Async WebSockets** — Real-time edge events via `wss://` (not HTTP polling)
✅ **Message Queue** — Decouples blockchain ingestion from database writes
✅ **Welford's Algorithm** — True Z-score calculation without loading all history
✅ **Container Ready** — Dockerfile + docker-compose.prod.yml for easy scaling
✅ **Health Checks** — Database health checks before starting services
✅ **Background Retraining** — ML model updates hourly with fresh data

### Next Steps (Post-Launch):
1. **Replace Mock ABI** — Use real Polymarket contract ABI from PolygonScan
2. **Add WebSocket Resilience** — Implement automatic reconnection with exponential backoff
3. **Historical Backfill** — Load past 30 days of trades via Polymarket GraphQL API
4. **Advanced Features** — Market concentration entropy, coordinated cluster detection