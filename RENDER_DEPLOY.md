# StableFlow — Render Deployment Guide

## Services Overview

StableFlow is deployed as **3 independent services** on Render:

| Service | File | DB needed | URL pattern |
|---|---|---|---|
| `stableflow-payment-api` | `main.py` | ✅ PostgreSQL | `payment-api.onrender.com` |
| `stableflow-routing-engine` | `routing_main.py` | ❌ Stateless | `routing-engine.onrender.com` |
| `stableflow-webhook-service` | `webhook_main.py` | ✅ Shared DB | `webhook-service.onrender.com` |

All three share the **same GitHub repo** — Render just runs a different start command per service.

---

## Prerequisites

- [ ] GitHub account with this repo pushed
- [ ] Render account at [render.com](https://render.com) (free tier works)
- [ ] BNB Chain wallet address + private key
- [ ] Anthropic API key (optional — routing works without it)

---

## Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: StableFlow initial commit"
git remote add origin https://github.com/YOUR_USERNAME/stableflow.git
git push -u origin main
```

---

## Step 2 — Deploy the PostgreSQL Database

> ⚠️ Do this FIRST — the payment-api and webhook services depend on it.

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New → PostgreSQL**
3. Fill in:
   - **Name:** `stableflow-db`
   - **Database:** `stableflow`
   - **User:** `stableflow`
   - **Region:** Oregon (or your preferred region — must match services)
   - **Plan:** Free
4. Click **Create Database**
5. Copy the **Internal Database URL** — you'll need it below

---

## Step 3 — Deploy the Payment API

1. Click **New → Web Service**
2. Connect your GitHub repo
3. Fill in:
   - **Name:** `stableflow-payment-api`
   - **Region:** Same as your DB (Oregon)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

4. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Paste the Internal URL from Step 2 |
   | `BNB_RPC_URL` | `https://bsc-dataseed.binance.org/` |
   | `MERCHANT_WALLET_ADDRESS` | Your BNB wallet address |
   | `MERCHANT_PRIVATE_KEY` | Your BNB wallet private key |
   | `SECRET_KEY` | Click **Generate** |
   | `WEBHOOK_SECRET` | Choose a strong secret string |
   | `ANTHROPIC_API_KEY` | Your Anthropic key (or leave blank) |
   | `USDT_CONTRACT` | `0x55d398326f99059fF775485246999027B3197955` |
   | `USDC_CONTRACT` | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` |

5. Under **Health Check Path:** `/health`
6. Click **Create Web Service**

> ✅ After deploy, visit: `https://stableflow-payment-api.onrender.com/docs`

---

## Step 4 — Deploy the Routing Engine

1. Click **New → Web Service**
2. Connect the **same GitHub repo**
3. Fill in:
   - **Name:** `stableflow-routing-engine`
   - **Region:** Same region
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn routing_main:app --host 0.0.0.0 --port $PORT`

4. Environment Variables:

   | Key | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | Your Anthropic key (or leave blank for fallback) |
   | `SECRET_KEY` | Click **Generate** |

5. **Health Check Path:** `/health`
6. Click **Create Web Service**

> ✅ After deploy: `https://stableflow-routing-engine.onrender.com/docs`

---

## Step 5 — Deploy the Webhook Service

1. Click **New → Web Service**
2. Connect the **same GitHub repo**
3. Fill in:
   - **Name:** `stableflow-webhook-service`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn webhook_main:app --host 0.0.0.0 --port $PORT`

4. Environment Variables:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Same Internal DB URL from Step 2 |
   | `WEBHOOK_SECRET` | **Exact same value** as in payment-api |
   | `SECRET_KEY` | Click **Generate** |

5. **Health Check Path:** `/health`
6. Click **Create Web Service**

---

## Step 6 — Verify All Services

```bash
# Payment API
curl https://stableflow-payment-api.onrender.com/health

# Routing Engine
curl https://stableflow-routing-engine.onrender.com/health

# Webhook Service
curl https://stableflow-webhook-service.onrender.com/health

# Test routing
curl -X POST https://stableflow-routing-engine.onrender.com/api/v1/routing/route \
  -H "Content-Type: application/json" \
  -d '{"sender_country":"US","receiver_country":"IN","amount_usd":500,"token":"USDT"}'
```

---

## Important Notes

### Free Tier Behaviour
Render's free tier **spins down after 15 minutes of inactivity** — the first request after idle takes ~30s to wake up. For a hackathon demo this is fine. Upgrade to the **Starter plan ($7/mo)** for always-on.

### WEBHOOK_SECRET must match
The `WEBHOOK_SECRET` in `stableflow-payment-api` and `stableflow-webhook-service` **must be identical** — HMAC signing breaks if they differ.

### Private Key Security
Never commit `MERCHANT_PRIVATE_KEY` to git. Always set it via the Render dashboard environment variables UI.

### Database on Free Tier
Render's free PostgreSQL has a **90-day expiry** — you'll need to create a new one or upgrade before then.

---

## Final Architecture on Render

```
GitHub Repo (single)
       │
       ├── main.py          → stableflow-payment-api.onrender.com
       ├── routing_main.py  → stableflow-routing-engine.onrender.com
       └── webhook_main.py  → stableflow-webhook-service.onrender.com
                                        │
                               stableflow-db (PostgreSQL)
                           shared by payment-api + webhook-service
```
