from fastapi import APIRouter, HTTPException
from app.models.schemas import RouteRequestBody
from app.services.routing_engine import (
    RoutingEngine, RouteRequest, ComplianceError, NoRouteError
)
from app.services.explanation_service import explain_route

router = APIRouter()
engine = RoutingEngine()


@router.post("/route")
async def get_route(body: RouteRequestBody):
    """
    AI Routing Engine endpoint.

    Returns the optimal stablecoin settlement route for a cross-border payment.

    Architecture:
    - Rule engine makes the deterministic decision (auditable, compliant)
    - Claude explains the decision in plain English (UX layer only)
    """
    req = RouteRequest(
        sender_country=body.sender_country.upper(),
        receiver_country=body.receiver_country.upper(),
        amount_usd=body.amount_usd,
        token=body.token,
        strategy=body.strategy,
        user_kyc_level=body.user_kyc_level,
    )

    try:
        decision = engine.route(req)
    except ComplianceError as e:
        raise HTTPException(status_code=451, detail={
            "error": "COMPLIANCE_BLOCKED",
            "message": str(e),
            "compliance_notes": e.notes,
        })
    except NoRouteError as e:
        raise HTTPException(status_code=422, detail={
            "error": "NO_ROUTE_AVAILABLE",
            "message": str(e),
            "rejected_providers": e.rejected,
        })

    if body.include_explanation:
        decision.explanation = await explain_route(req, decision)

    p = decision.selected_provider
    return {
        "route": {
            "provider": p.provider,
            "method": p.method,
            "token": body.token,
            "settlement_chain": "BNB Chain (BEP-20)",
        },
        "financials": {
            "amount_sent_usd": body.amount_usd,
            "total_fee_usd": decision.total_fee_usd,
            "fee_pct_effective": decision.fee_pct_effective,
            "estimated_received_usd": decision.estimated_received_usd,
            "settlement_minutes": decision.settlement_minutes,
        },
        "strategy_used": body.strategy,
        "explanation": decision.explanation,
        "compliance": {
            "passed": decision.compliance_passed,
            "notes": decision.compliance_notes,
        },
        "audit": {
            "composite_score": decision.score,
            "rejected_providers": decision.rejected_providers,
        },
    }


@router.get("/corridors")
async def list_supported_corridors():
    """Returns all active Binance P2P corridors."""
    from app.services.routing_engine import BINANCE_P2P_CORRIDORS
    return {
        "provider": "Binance P2P",
        "corridors": [
            {"sender": s, "receiver": r}
            for s, r in sorted(BINANCE_P2P_CORRIDORS)
        ],
        "total": len(BINANCE_P2P_CORRIDORS),
    }
