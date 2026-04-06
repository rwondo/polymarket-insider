# Production Deployment Checklist

Complete this checklist before deploying your Polymarket Insider Detection system to production.

---

## Phase 1: Pre-Deployment (Local Testing)

### Environment Setup
- [ ] Python 3.11+ installed
- [ ] Docker & Docker Compose installed
- [ ] Git initialized (`.gitignore` configured)
- [ ] Virtual environment created (optional but recommended)

### API Keys Obtained
- [ ] **Alchemy Account Created** — https://alchemy.com
  - [ ] Polygon Mainnet app created
  - [ ] POLYGON_RPC_URL copied (https://)
  - [ ] POLYGON_WSS_URL copied (wss://)
  - [ ] API key saved securely (not shared)
  
- [ ] **Discord Webhook Created** — https://discord.com
  - [ ] Server created or selected
  - [ ] #alerts channel created
  - [ ] Webhook generated in channel settings
  - [ ] WEBHOOK_URL copied
  - [ ] **Test webhook locally** with curl command from API_KEYS_SETUP.md

- [ ] **Database Prepared**
  - [ ] For local: Default postgres credentials ready
  - [ ] For production: Neon/RDS/Supabase account created
  - [ ] DATABASE_URL obtained

### Configuration Files
- [ ] `.env` file created in project root with:
  - [ ] POLYGON_RPC_URL (Alchemy https endpoint)
  - [ ] POLYGON_WSS_URL (Alchemy wss endpoint)
  - [ ] WEBHOOK_URL (Discord webhook)
  - [ ] DATABASE_URL (postgres connection string)
- [ ] `.env` file added to `.gitignore` (prevent accidental commits)
- [ ] `.env.example` committed to git (template for others)

### Local Testing (30+ minutes)
- [ ] `docker-compose up -d` starts without errors
- [ ] `pip install -r requirements.txt` completes successfully
- [ ] `python main.py` outputs:
  - [ ] "Listening for trades on ... via WSS..."
  - [ ] "Started Queue Processor Worker"
  - [ ] No connection errors after 5 minutes
- [ ] API server runs: `uvicorn src.api.main:app --reload`
  - [ ] Accessible at http://127.0.0.1:8000
  - [ ] Swagger docs load at http://127.0.0.1:8000/docs
  - [ ] `/api/anomalies` returns valid JSON
- [ ] Logs show no errors for 30+ minutes of continuous running

---

## Phase 2: Pre-Production Infrastructure

### Cloud Provider Selection
- [ ] Server provider chosen:
  - [ ] EC2 (AWS) — t3.small or larger
  - [ ] DigitalOcean App Platform or Droplet
  - [ ] Railway.app
  - [ ] Render
  - [ ] Other: __________

### Server Setup
- [ ] Server created in chosen cloud provider
- [ ] OS: Ubuntu 22.04 LTS or Debian 12+ selected
- [ ] SSH key pair generated and securely stored
- [ ] Inbound ports allowed: 22 (SSH), 8000 (API)
- [ ] Outbound ports allowed: 443 (HTTPS for RPC & webhooks)

### Server Dependencies
- [ ] SSH into server successful
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] Git installed: `git --version`
- [ ] SSH keys are on the server for git pull

### Production Environment File
- [ ] Create `.env.prod` locally (or `.env` on server)
- [ ] Copy from local `.env` to `/app/.env` on server using:
  ```bash
  scp -i your-key.pem .env user@server:/app/.env
  ```
  **OR** create it directly on the server using a secure method (NOT email)
- [ ] Permissions set: `chmod 600 .env`

---

## Phase 3: Deployment

### Clone Repository
```bash
ssh -i your-key.pem user@server
git clone https://github.com/YOUR_USERNAME/polymarket-insider.git /app
cd /app
```

- [ ] Repository cloned to `/app` on server
- [ ] `.env` file in place (see Phase 2)

### Build & Start Services
```bash
cd /app
docker-compose -f docker-compose.prod.yml up -d --build
```

- [ ] Build completes without errors
- [ ] All services start: `docker-compose -f docker-compose.prod.yml ps`
  - [ ] `db` shows `(healthy)`
  - [ ] `worker` shows status `Up`
  - [ ] `api` shows status `Up` with port `8000`

### Verify Services
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f worker

# Expected output (within 30 seconds):
# INFO - Listening for trades on ... via WSS...
# INFO - Started Queue Processor Worker
```

- [ ] Worker logs show WebSocket connection
- [ ] No errors in logs after 5 minutes

### API Verification
```bash
# From your local machine:
curl http://YOUR_SERVER_IP:8000/
# Should return: {"status":"System Online",...}

curl http://YOUR_SERVER_IP:8000/api/anomalies
# Should return a JSON array: []
```

- [ ] API responds to requests
- [ ] Swagger docs load: http://YOUR_SERVER_IP:8000/docs

---

## Phase 4: Post-Deployment

### Monitoring
- [ ] Set up continuous log monitoring:
  ```bash
  docker-compose -f docker-compose.prod.yml logs -f
  ```
- [ ] Configure log aggregation (optional) — Datadog, CloudWatch, or similar
- [ ] Set up server alerts (CPU, memory, disk) if available through provider

### Database Backups
- [ ] Set up automated backups (if using managed DB service)
- [ ] Test restore procedure (critical!)
- [ ] Establish backup retention policy (e.g., 30 days)

### Webhook Testing
- [ ] Manually send test alert to Discord:
  ```bash
  docker-compose -f docker-compose.prod.yml exec api python -c "
  from src.notifier.webhook import send_alert
  send_alert({
    'wallet_address': '0xtest123',
    'market_id': '0xtest456',
    'score': 95.0,
    'trade_size': 5000.0,
    'explanation': 'Test alert - System is live!'
  })
  "
  ```
- [ ] Verify Discord receives the test alert

### Performance Baseline
- [ ] Record initial metrics:
  - [ ] CPU usage (should be <20%)
  - [ ] Memory usage (should be <2GB)
  - [ ] RTT to blockchain node (<100ms ideally)
  - [ ] Database latency (<10ms ideally)

---

## Phase 5: Scaling & Optimization (Post-Launch)

### Real Contract Integration
- [ ] Obtain real Polymarket contract ABI from PolygonScan
- [ ] Update `POLYMARKET_CTF_ADDRESS` in `config.py`
- [ ] Replace mock ABI in `polygon_client.py` with real ABI
- [ ] Test against real contract events

### WebSocket Resilience
- [ ] Implement automatic reconnection logic (exp. backoff)
- [ ] Add circuit breaker pattern for failing RPCs
- [ ] Set up fallback RPC provider if available

### Historical Data Backfill
- [ ] Implement Polymarket GraphQL API integration
- [ ] Backfill last 30 days of trades
- [ ] Retrain ML model on historical data

### Advanced Features (Optional)
- [ ] Market concentration (entropy) calculation
- [ ] Coordinated wallet cluster detection (DBSCAN)
- [ ] Custom alert rules per market
- [ ] Dashboard UI (Streamlit or React)

---

## Emergency Procedures

### If Worker Crashes
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs worker

# Restart worker
docker-compose -f docker-compose.prod.yml restart worker

# Full restart if needed
docker-compose -f docker-compose.prod.yml up -d
```

- [ ] Auto-restart policy configured in docker-compose.prod.yml (default: always)

### If Database is Corrupted
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Backup data (if you can)
docker-compose -f docker-compose.prod.yml exec db pg_dump -U polymarket polymarket_insider > backup.sql

# Reset database
docker volume rm polymarket-insider_postgres_data_prod

# Restart
docker-compose -f docker-compose.prod.yml up -d
```

- [ ] Backup procedures documented
- [ ] Team understands recovery steps

### If WebSocket Connection Drops
**This is expected and handled by automatic reconnection logic.**
- [ ] Monitor logs: `docker-compose logs -f worker`
- [ ] Should see automatic reconnection attempts
- [ ] If reconnection fails after 5+ attempts, restart worker

---

## Final Sign-Off

- [ ] All checklist items completed
- [ ] System running stably for 24+ hours
- [ ] Alerts being received in Discord
- [ ] No critical errors in logs
- [ ] Backups automated and verified
- [ ] Team notified of production deployment
- [ ] Documentation updated with production URLs/IPs

🚀 **System is production-ready!**

---

## Support Contacts

- **RPC Issues**: Check Alchemy dashboard for quota usage
- **Discord Webhook**: Verify webhook URL hasn't changed
- **Database**: Check managed service dashboard for alerts
- **Code Issues**: Review logs with `docker-compose logs -f`