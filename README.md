# StableFlow 🌊

> **AI-Powered Stablecoin Payment Rails on BNB Chain**
> Built for the BNB Chain x Ignyte Global Innovation Challenge — Payments Theme

---

## Overview

StableFlow is a unified payment infrastructure that enables **frictionless stablecoin payments and cross-border settlements** for consumers and merchants — powered by BNB Chain and an AI-assisted routing engine.

### Core Modules

| Module | Description |
|---|---|
| **Payment API** | Stripe-like payment intents for USDT/USDC on BNB Chain |
| **AI Routing Engine** | Deterministic rule-based router + Claude for plain-English explanations |
| **Webhook System** | HMAC-SHA256 signed event delivery to merchant endpoints |
| **Compliance Engine** | OFAC/UN sanctions, FATF EDD, CTR thresholds — built-in |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   StableFlow API                    │
│                                                     │
│  POST /payments/intent   → Payment Intent           │
│  POST /payments/confirm  → On-chain Verification    │
│  POST /routing/route     → AI Route Decision        │
│  POST /merchants/register → Merchant Onboarding     │
└───────────────┬─────────────────────┬───────────────┘
                │                     │
       ┌────────▼────────┐   ┌────────▼────────────┐
       │   BNB Chain     │   │  AI Routing Engine  │
       │  (BEP-20 USDT/  │   │                     │
       │   USDC txns)    │   │  1. Compliance Gate │
       └─────────────────┘   │  2. Eligibility     │
                             │  3. Scoring Engine  │
                             │  4. Claude (explain)│
                             └─────────────────────┘
```

### AI Routing Design Philosophy

For a regulated fintech product, pure LLM routing is unsuitable:

| Concern | Our Solution |
|---|---|
| Determinism | Rule engine makes all decisions — same input = same output, always |
| Auditability | Full audit trail: every rejection reason is logged |
| Compliance | OFAC/FATF hard blocks before any routing logic runs |
| Latency | Rules execute in <1ms; Claude adds explanation async |
| Hallucination risk | Claude only explains — it cannot affect the routing decision |

**Claude's safe role:** Explains routing decisions in plain English for non-crypto users.

---

## Quick Start

### 1. Clone & Configure

```bash
git clone <repo>
cd stableflow
cp .env.example .env
# Fill in BNB_RPC_URL, MERCHANT_WALLET_ADDRESS, ANTHROPIC_API_KEY
```

### 2. Run with Docker (recommended)

```bash
make up
```

This starts:
- **StableFlow API** at `http://localhost:8000`
- **Swagger docs** at `http://localhost:8000/docs`
- **Webhook tester** at `http://localhost:9000`

### 3. Run locally (without Docker)

```bash
make install
make dev
```

### 4. Run tests

```bash
make test
```

---

## API Reference

### Payment Flow

```
1. Register merchant      POST /api/v1/merchants/register
2. Create payment intent  POST /api/v1/payments/intent
3. Customer sends USDT/USDC to payment_address on BNB Chain
4. Submit tx hash         POST /api/v1/payments/{id}/confirm
5. API verifies on-chain  (3 block confirmations)
6. Webhook fires          HMAC-signed POST to merchant endpoint
```

### AI Routing

```bash
curl -X POST http://localhost:8000/api/v1/routing/route \
  -H "Content-Type: application/json" \
  -d '{
    "sender_country": "US",
    "receiver_country": "IN",
    "amount_usd": 500,
    "token": "USDT",
    "strategy": "balanced"
  }'
```

**Response:**
```json
{
  "route": {
    "provider": "Binance P2P",
    "method": "P2P",
    "token": "USDT",
    "settlement_chain": "BNB Chain (BEP-20)"
  },
  "financials": {
    "amount_sent_usd": 500,
    "total_fee_usd": 0.0,
    "fee_pct_effective": 0.0,
    "estimated_received_usd": 500.0,
    "settlement_minutes": 15
  },
  "explanation": "We're routing your payment via Binance P2P, which charges no fees for this transfer. Your recipient should receive the full $500.00 within approximately 15 minutes.",
  "compliance": { "passed": true, "notes": [] },
  "audit": {
    "composite_score": 0.892,
    "rejected_providers": [...]
  }
}
```

### Routing Strategies

| Strategy | Fee Weight | Speed Weight | Best for |
|---|---|---|---|
| `cheapest` | 70% | 10% | Maximum savings |
| `fastest` | 15% | 65% | Urgent transfers |
| `balanced` | 40% | 35% | Default — best overall |

### Compliance Responses

| Code | Error | Meaning |
|---|---|---|
| 451 | `COMPLIANCE_BLOCKED` | Sanctioned country or KYC insufficient |
| 422 | `NO_ROUTE_AVAILABLE` | No provider supports this corridor/amount |

---

## Project Structure

```
stableflow/
├── main.py                          # FastAPI entry point
├── Dockerfile
├── docker-compose.yml               # Full stack: API + webhook tester
├── Makefile                         # Dev shortcuts
├── requirements.txt
├── .env.example
├── app/
│   ├── core/
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   └── bnb_client.py            # Web3 + BEP-20 helpers
│   ├── models/
│   │   └── schemas.py               # All Pydantic models
│   ├── services/
│   │   ├── payment_service.py       # Payment intent logic + BNB verification
│   │   ├── routing_engine.py        # Rule-based routing core
│   │   ├── explanation_service.py   # Claude explanation layer
│   │   └── webhook_service.py       # HMAC-signed webhook delivery
│   └── routers/
│       ├── payments.py
│       ├── merchants.py
│       ├── webhooks.py
│       └── routing.py
└── tests/
    └── test_all.py                  # Full test suite
```

---

## Scoring Criteria Alignment

| Criterion | How StableFlow addresses it |
|---|---|
| **BNB Chain relevance** | Native BEP-20 USDT/USDC; Binance P2P as primary off-ramp |
| **Technical feasibility** | FastAPI + Web3.py + on-chain tx verification |
| **UX & accessibility** | Claude explains routing in plain English; Stripe-like payment intents |
| **Innovation** | Hybrid deterministic+AI architecture; compliance-safe LLM usage |
| **Real-world fit** | $800B+ remittance market; 0% fees via Binance P2P |
| **Open Source** | All scoring weights, compliance rules, and routing logic are transparent |

---

## License

MIT
