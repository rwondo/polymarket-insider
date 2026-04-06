# Quick Start Checklist

Use this to verify you have everything needed before running the system.

## Pre-Deployment Checklist

### 1. API Keys Obtained ✓
- [ ] Alchemy account created (https://alchemy.com)
- [ ] Polygon app created in Alchemy dashboard
- [ ] POLYGON_RPC_URL copied from Alchemy
- [ ] POLYGON_WSS_URL copied from Alchemy
- [ ] Discord server created (https://discord.com)
- [ ] Discord webhook created in #alerts channel
- [ ] WEBHOOK_URL copied from Discord

### 2. Environment File Created ✓
- [ ] `.env` file created in project root
- [ ] POLYGON_RPC_URL added to .env
- [ ] POLYGON_WSS_URL added to .env
- [ ] WEBHOOK_URL added to .env
- [ ] DATABASE_URL set to local postgres (default)
- [ ] .env file is NOT tracked by git (check .gitignore)

### 3. Local Testing ✓
```powershell
# Run these commands in order:

# 1. Start database
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the system (should see logs below)
python main.py
```

**Expected output on startup:**
```
2026-04-06 ... INFO - Starting Polymarket Insider Detection System...
2026-04-06 ... INFO - Listening for trades on ... via WSS...
2026-04-06 ... INFO - Started Queue Processor Worker.
```

**No errors = You're ready!**

---

## Next: Production Deployment

Once local testing works for 30+ minutes without errors:

1. **Create production server** (EC2, DigitalOcean, Railway, Render, etc.)
2. **Copy `.env` to server** (securely, not in git!)
3. **Run on server:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
4. **Verify services:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   # Should show: db (healthy), worker (healthy), api (running)
   ```
5. **Check logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f worker
   ```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'web3'` | Run `pip install -r requirements.txt` |
| `psycopg2` error | Ensure `docker-compose up -d` is running |
| WSS connection timeout | Check your Alchemy API key in POLYGON_WSS_URL |
| No Discord alerts received | Test webhook with `curl` command from API_KEYS_SETUP.md |

---

## File Structure (For Reference)

```
polymarket arbitrage/
├── .env                          (Create this, DO NOT commit)
├── .env.example                  (Template - can commit)
├── .gitignore                    (Prevents .env from leaking)
├── main.py                       (Main orchestrator - async)
├── requirements.txt              (Python packages)
├── Dockerfile                    (Container build)
├── docker-compose.yml            (Local dev environment)
├── docker-compose.prod.yml       (Production environment)
├── API_KEYS_SETUP.md             (Detailed API key guide)
├── QUICK_START.md                (This file)
├── README.md                     (Project overview)
└── src/
    ├── api/
    │   └── main.py               (FastAPI endpoints)
    ├── config.py                 (Pydantic settings)
    ├── db/
    │   ├── database.py           (SQLAlchemy setup)
    │   └── models.py             (ORM tables)
    ├── features/
    │   └── feature_engineer.py   (Welford's algorithm)
    ├── ingestion/
    │   └── polygon_client.py     (AsyncWeb3 WebSocket)
    ├── models/
    │   └── anomaly_detector.py   (IsolationForest)
    └── notifier/
        └── webhook.py            (Discord alerts)
```

---

## Support & Monitoring

**Local Development:**
- API docs: http://localhost:8000/docs
- Logs: Watch the terminal output

**Production Monitoring:**
- Check worker logs: `docker-compose -f docker-compose.prod.yml logs worker`
- Check API logs: `docker-compose -f docker-compose.prod.yml logs api`
- Database query: Connect to the PostgreSQL instance directly

**Common Queries:**
```sql
-- Top flagged wallets
SELECT wallet_address, COUNT(*), AVG(score)
FROM anomalies
GROUP BY wallet_address
ORDER BY AVG(score) DESC
LIMIT 10;

-- Recent anomalies
SELECT * FROM anomalies
ORDER BY timestamp DESC
LIMIT 50;
```

---

## What This System Does

✅ Monitors Polymarket on Polygon in real-time via WebSockets
✅ Calculates Z-scores using Welford's algorithm (statistically accurate)
✅ Detects insider-like trading patterns with IsolationForest ML
✅ Sends Discord alerts when score exceeds threshold (default 80)
✅ Stores all trades & anomalies in PostgreSQL for analysis
✅ Provides REST API endpoints for querying results
✅ Scales to production with Docker & containerization

**Current Limitations:**
- Uses mock Polymarket ABI (replace with real ABI from PolygonScan)
- Single WebSocket connection (add reconnection logic for resilience)
- Hourly model retraining stub (implement full training pipeline)

**Next Improvements After Launch:**
1. Real Polymarket contract ABIs + addresses
2. WebSocket reconnection with exponential backoff
3. Historical data backfill from Polymarket GraphQL API
4. Dashboard UI (Streamlit or React)
5. Advanced features: market concentration, coordinated wallet clusters