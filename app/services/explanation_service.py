"""
Claude Explanation Layer.

Design contract:
  - Claude does NOT make routing decisions
  - Claude ONLY explains decisions already made by the rule engine
  - Falls back silently to a template — never blocks payment flow
  - Output is UX copy only, never consumed by transaction logic
"""

import httpx
import json
import logging
from app.services.routing_engine import RouteDecision, RouteRequest
from app.core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a helpful payment assistant for StableFlow, a stablecoin payments platform on BNB Chain.

Your ONLY job is to explain a routing decision already made by our deterministic rule engine.
Rules:
- Do NOT suggest alternative routes or question the decision
- Do NOT provide financial advice
- Keep it to 2–3 sentences maximum
- Be specific: mention the provider name, fee amount, and settlement time
- Write in plain English that a non-crypto user understands
- Do not use jargon like "liquidity", "corridors", or "BEP-20"
- If there are compliance notes (e.g. EDD required), mention them simply and calmly"""


async def explain_route(req: RouteRequest, decision: RouteDecision) -> str:
    """
    Calls Claude to generate a plain-English explanation.
    Falls back to a deterministic template on any failure.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.info("No Anthropic API key configured — using fallback explanation")
        return _fallback(req, decision)

    payload = {
        "sender_country": req.sender_country,
        "receiver_country": req.receiver_country,
        "amount_usd": req.amount_usd,
        "token": req.token,
        "strategy": req.strategy.value,
        "selected_provider": decision.selected_provider.provider,
        "method": decision.selected_provider.method,
        "total_fee_usd": decision.total_fee_usd,
        "estimated_received_usd": decision.estimated_received_usd,
        "settlement_minutes": decision.settlement_minutes,
        "compliance_notes": decision.compliance_notes,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                CLAUDE_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 150,
                    "system": SYSTEM_PROMPT,
                    "messages": [{
                        "role": "user",
                        "content": f"Explain this routing decision in plain English:\n\n{json.dumps(payload, indent=2)}"
                    }],
                },
            )
            resp.raise_for_status()
            explanation = resp.json()["content"][0]["text"].strip()
            logger.info("Claude explanation generated for %s→%s $%.2f",
                        req.sender_country, req.receiver_country, req.amount_usd)
            return explanation

    except Exception as e:
        logger.warning("Claude explanation failed, using fallback: %s", e)
        return _fallback(req, decision)


def _fallback(req: RouteRequest, d: RouteDecision) -> str:
    """Zero-dependency fallback. Always works."""
    p = d.selected_provider
    fee_str = f"${d.total_fee_usd:.2f}" if d.total_fee_usd > 0 else "no fee"
    return (
        f"We're routing your {req.token} payment via {p.provider} ({p.method}), "
        f"charging {fee_str} for this transfer. "
        f"Your recipient should receive ${d.estimated_received_usd:.2f} "
        f"within approximately {d.settlement_minutes} minutes."
    )
