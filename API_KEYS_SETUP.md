# API Keys Setup Guide for Polymarket Insider Detection System

## Overview
You need API keys from 3 main services:
1. **Alchemy** - Polygon RPC + WebSockets (critical)
2. **Discord or Telegram** - For alerts
3. **PostgreSQL** - Database (default local credentials, or managed service)

---

## Step 1: Get Polygon RPC & WSS Endpoints from Alchemy

### Why Alchemy?
- Free tier includes 300M compute units/month (sufficient for real-time monitoring)
- Dedicated RPC endpoint (not rate-limited like public endpoints)
- Automatic failover and reliability
- WebSocket support for instant event streaming

### How to Set Up:

1. **Go to https://alchemy.com**
2. **Click "Sign Up"** (top right)
3. **Complete registration** with email
4. **Verify email** (check spam folder)
5. **Log in** to the dashboard
6. **Click "Create App"** or "New App"
   - Select: **Network** = "Polygon"
   - Select: **Chain** = "Mainnet" (NOT Mumbai testnet)
   - Give it a name: "Polymarket Insider"
   - Click **"Create App"**
7. **Copy your endpoints:**
   - On the app card, click **"View Key"**
   - You'll see a modal with:
     - **HTTPS URL** (starts with `https://polygon-mainnet.g.alchemy.com/v2/...`)
     - **WebSocket URL** (starts with `wss://polygon-mainnet.g.alchemy.com/v2/...`)
   - **Copy both** — you'll need them for your `.env` file

### Save These Values:
```
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
POLYGON_WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

---

## Step 2: Get Discord Webhook URL (For Alerts)

### Why Discord?
- Free
- Easy to set up
- Instant notifications
- Embeds for pretty formatting

### How to Set Up:

1. **Open your Discord Server** (or create a new one)
   - If you don't have Discord, go to https://discord.com and sign up first
2. **Create a new channel** for polymarket alerts
   - Right-click on your server → **"Create Channel"**
   - Name: `#polymarket-alerts` (or any name)
3. **Create a Webhook:**
   - Right-click the channel → **"Edit Channel"**
   - Left sidebar: Click **"Integrations"**
   - Click **"Webhooks"** tab
   - Click **"New Webhook"**
   - Name it: "Polymarket Insider Bot"
   - Click **"Copy Webhook URL"**
4. **Save the URL:**
   ```
   WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
   ```

**Test it locally:**
```bash
curl -X POST https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN \
  -H "Content-Type: application/json" \
  -d '{"content":"Test alert from Polymarket Insider"}'
```

---

## Step 3 (ALTERNATIVE): Get Telegram Bot Token & Chat ID

### If You Prefer Telegram Over Discord:

1. **Open Telegram** (web.telegram.org or mobile app)
2. **Search for:** `@BotFather`
3. **Start conversation** with BotFather
4. **Send:** `/newbot`
   - Choose a name: "PolymarketInsiderBot"
   - Choose a username: "polymarket_insider_bot_YOURNAME"
5. **Copy the token** (looks like `123456789:ABCDefGhIjklMnoPqrSTuvWxyz`)
   ```
   TELEGRAM_TOKEN=123456789:ABCDefGhIjklMnoPqrSTuvWxyz
   ```
6. **Get your Chat ID:**
   - Create or find a private group/channel
   - Add your bot to it
   - Send a message: `/start`
   - Go to `https://api.telegram.org/bot{TOKEN}/getUpdates`
   - Replace `{TOKEN}` with your token from step 5
   - Look for `"chat":{"id":123456789}`
   ```
   TELEGRAM_CHAT_ID=123456789
   ```

---

## Step 4: PostgreSQL Database

### Option A: Local Testing (Development)
Use the default credentials from `docker-compose.yml`:
```
DB_USER=polymarket
DB_PASSWORD=password
DATABASE_URL=postgresql://polymarket:password@localhost:5432/polymarket_insider
```

### Option B: Production (Managed Service)
Use a managed PostgreSQL provider:

#### **Neon** (Recommended - Free serverless Postgres)
1. Go to https://neon.tech
2. Sign up with email
3. Create a new **"Project"**
4. Copy the connection string:
   ```
   DATABASE_URL=postgresql://user:password@ep-XXXXX.us-east-1.neon.tech/polymarket_insider
   ```

#### **AWS RDS** (Most reliable but costs $)
1. Go to AWS Console → RDS
2. Click **"Create database"**
3. Engine: PostgreSQL 15
4. Instance class: `db.t3.micro` (free tier eligible)
5. Copy endpoint after creation:
   ```
   DATABASE_URL=postgresql://admin:PASSWORD@polymarket-db.XXXXX.us-east-1.rds.amazonaws.com:5432/polymarket_insider
   ```

#### **Supabase** (PostgreSQL + extras, free tier available)
1. Go to https://supabase.com
2. Sign up
3. Create a new project (Free tier)
4. Go to **Settings** → **Database**
5. Copy the PostgreSQL URI:
   ```
   DATABASE_URL=postgresql://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres
   ```

---

## Step 5: Create Your `.env` File

In the root of your project (`c:\Users\39392\OneDrive\Desktop\polymarket arbitrage\`), create a file named `.env`:

```env
# Polygon RPC (from Alchemy)
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE
POLYGON_WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY_HERE

# Discord Webhook (for alerts)
WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Database
DATABASE_URL=postgresql://polymarket:password@localhost:5432/polymarket_insider

# (Optional) Telegram instead of Discord
# TELEGRAM_TOKEN=YOUR_TOKEN
# TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

---

## Step 6: Verify Everything Works Locally

Before deploying, test the entire pipeline:

```powershell
# 1. Start local database
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the system
python main.py
```

Watch for these log messages:
- ✅ `Listening for trades on ... via WSS...`
- ✅ `Started Queue Processor Worker`
- ✅ No connection errors in logs

To test Discord alerts manually, edit `main.py` temporarily to send a test alert:
```python
from src.notifier.webhook import send_alert

# Add this after the logger setup
send_alert({
    "wallet_address": "0xtest",
    "market_id": "0xtest",
    "score": 95.0,
    "trade_size": 5000.0,
    "explanation": "Test alert - system is working!"
})
```

---

## Step 7: Checklist Before Production

- [ ] Alchemy app created and WSS URL copied
- [ ] Discord server + webhook created
- [ ] `.env` file saved locally with all keys
- [ ] Database credentials validated (local or managed service)
- [ ] `python main.py` runs without errors for 2+ minutes
- [ ] Discord webhook test alert received
- [ ] No sensitive info committed to Git (add `.env` to `.gitignore`)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `wss://` connection timeout | Make sure you're using Alchemy (not public endpoint). Free tier has enough throughput. |
| Discord webhook 401 error | Copy the FULL webhook URL including the token. Check it 3 times. |
| PostgreSQL connection refused | Ensure `docker-compose up -d` is running or your managed DB is accessible. |
| No trades detected | This is normal if market is slow. Polymarket has ~500-5000 trades/day. Keep it running to see events. |

---

## Next Steps

Once all keys are in place:
1. Run locally for 24 hours to validate
2. Deploy to EC2/DigitalOcean using `docker-compose.prod.yml`
3. Set up log monitoring (CloudWatch, Datadog, or similar)
4. Configure alerting thresholds in `src/config.py`