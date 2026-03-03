"""
StableFlow AI Routing Engine
Architecture: Rule-based core (deterministic, auditable) + Claude for UX explanation only
"""

from dataclasses import dataclass, field
from typing import Optional
import logging
from app.models.schemas import RoutingStrategy

logger = logging.getLogger(__name__)


# ─── Internal Data Models ─────────────────────────────────────────────────────

@dataclass
class RouteRequest:
    sender_country: str
    receiver_country: str
    amount_usd: float
    token: str = "USDT"
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    user_kyc_level: int = 1


@dataclass
class ProviderOption:
    provider: str
    method: str
    fee_pct: float
    flat_fee_usd: float
    settlement_minutes: int
    min_amount_usd: float
    max_amount_usd: float
    supported_tokens: list
    requires_kyc_level: int
    availability_score: float
    compliance_flags: list = field(default_factory=list)


@dataclass
class RouteDecision:
    selected_provider: ProviderOption
    total_fee_usd: float
    fee_pct_effective: float
    estimated_received_usd: float
    settlement_minutes: int
    score: float
    rejected_providers: list
    compliance_passed: bool
    compliance_notes: list
    explanation: Optional[str] = None


# ─── Provider Registry ────────────────────────────────────────────────────────

PROVIDER_REGISTRY: list[ProviderOption] = [
    ProviderOption(
        provider="Binance P2P", method="P2P",
        fee_pct=0.0, flat_fee_usd=0.0,
        settlement_minutes=15,
        min_amount_usd=10.0, max_amount_usd=50_000.0,
        supported_tokens=["USDT", "USDC"],
        requires_kyc_level=1, availability_score=0.92,
    ),
    ProviderOption(
        provider="MoonPay", method="bank_transfer",
        fee_pct=1.5, flat_fee_usd=3.99,
        settlement_minutes=60,
        min_amount_usd=20.0, max_amount_usd=10_000.0,
        supported_tokens=["USDT", "USDC"],
        requires_kyc_level=1, availability_score=0.97,
    ),
    ProviderOption(
        provider="Transak", method="bank_transfer",
        fee_pct=0.99, flat_fee_usd=1.50,
        settlement_minutes=45,
        min_amount_usd=15.0, max_amount_usd=15_000.0,
        supported_tokens=["USDT", "USDC"],
        requires_kyc_level=1, availability_score=0.94,
    ),
]

# OFAC / UN sanctioned — hard block
BLOCKED_COUNTRIES = {"IR", "KP", "SY", "CU", "SD", "MM", "BY", "RU"}

# FATF grey list — enhanced due diligence required
HIGH_RISK_COUNTRIES = {"AF", "HT", "LA", "MZ", "TZ", "YE", "ZW", "PK"}

# Binance P2P active corridors (high liquidity verified)
BINANCE_P2P_CORRIDORS = {
    ("US","IN"),("US","PH"),("US","NG"),("US","VN"),
    ("GB","IN"),("GB","PH"),("GB","NG"),
    ("SG","IN"),("SG","PH"),("SG","VN"),("SG","ID"),
    ("AE","IN"),("AE","PK"),("AE","PH"),
    ("IN","US"),("PH","US"),("NG","US"),
    ("IN","PK"),("PH","ID"),("NG","GH"),("KE","NG"),
}


# ─── Compliance Engine ────────────────────────────────────────────────────────

class ComplianceEngine:
    """Hard rules. Every decision is logged. Must pass before any scoring."""

    def check(self, req: RouteRequest) -> tuple[bool, list[str]]:
        notes, passed = [], True

        if req.sender_country.upper() in BLOCKED_COUNTRIES:
            notes.append(f"BLOCKED: Sender country {req.sender_country} is sanctioned (OFAC/UN)")
            passed = False

        if req.receiver_country.upper() in BLOCKED_COUNTRIES:
            notes.append(f"BLOCKED: Receiver country {req.receiver_country} is sanctioned (OFAC/UN)")
            passed = False

        if req.sender_country.upper() in HIGH_RISK_COUNTRIES:
            notes.append(f"EDD_REQUIRED: Sender {req.sender_country} needs enhanced due diligence")

        if req.receiver_country.upper() in HIGH_RISK_COUNTRIES:
            notes.append(f"EDD_REQUIRED: Receiver {req.receiver_country} needs enhanced due diligence")

        if req.amount_usd >= 10_000:
            notes.append("CTR_THRESHOLD: Amount >= $10,000 triggers Currency Transaction Report requirement")

        if req.amount_usd >= 3_000 and req.user_kyc_level < 2:
            notes.append("KYC_UPGRADE_REQUIRED: Full KYC required for amounts >= $3,000")
            passed = False

        return passed, notes


# ─── Scoring Engine ───────────────────────────────────────────────────────────

class ScoringEngine:
    """Composite score. Weights are explicit and strategy-driven. No black box."""

    WEIGHTS = {
        RoutingStrategy.CHEAPEST: {"fee": 0.70, "speed": 0.10, "availability": 0.20},
        RoutingStrategy.FASTEST:  {"fee": 0.15, "speed": 0.65, "availability": 0.20},
        RoutingStrategy.BALANCED: {"fee": 0.40, "speed": 0.35, "availability": 0.25},
    }

    def score(self, provider: ProviderOption, req: RouteRequest) -> float:
        w = self.WEIGHTS[req.strategy]
        fee_usd = (provider.fee_pct / 100) * req.amount_usd + provider.flat_fee_usd
        return round(
            w["fee"] * max(0.0, 1.0 - fee_usd / 50.0)
            + w["speed"] * max(0.0, 1.0 - provider.settlement_minutes / 120.0)
            + w["availability"] * provider.availability_score,
            4
        )


# ─── Main Routing Engine ──────────────────────────────────────────────────────

class RoutingEngine:

    def __init__(self):
        self.compliance = ComplianceEngine()
        self.scoring    = ScoringEngine()

    def route(self, req: RouteRequest) -> RouteDecision:
        # 1. Compliance gate — hard block
        passed, notes = self.compliance.check(req)
        if not passed:
            raise ComplianceError("; ".join(notes), notes=notes)

        # 2. Filter eligible providers
        eligible, rejected = [], []
        corridor = (req.sender_country.upper(), req.receiver_country.upper())

        for p in PROVIDER_REGISTRY:
            reasons = []
            if req.token not in p.supported_tokens:
                reasons.append(f"Token {req.token} not supported")
            if req.amount_usd < p.min_amount_usd:
                reasons.append(f"Amount ${req.amount_usd} below minimum ${p.min_amount_usd}")
            if req.amount_usd > p.max_amount_usd:
                reasons.append(f"Amount ${req.amount_usd} exceeds maximum ${p.max_amount_usd}")
            if req.user_kyc_level < p.requires_kyc_level:
                reasons.append(f"KYC {req.user_kyc_level} insufficient (need {p.requires_kyc_level})")
            if p.provider == "Binance P2P" and corridor not in BINANCE_P2P_CORRIDORS:
                reasons.append(f"Corridor {corridor} not active on Binance P2P")

            if reasons:
                rejected.append({"provider": p.provider, "reasons": reasons})
            else:
                eligible.append(p)

        if not eligible:
            raise NoRouteError(
                f"No providers for {req.sender_country}→{req.receiver_country} ${req.amount_usd} {req.token}",
                rejected=rejected
            )

        # 3. Score and rank
        scored = sorted(eligible, key=lambda p: self.scoring.score(p, req), reverse=True)
        best   = scored[0]
        best_score = self.scoring.score(best, req)

        for runner in scored[1:]:
            rejected.append({
                "provider": runner.provider,
                "reasons": [f"Score {self.scoring.score(runner, req):.4f} < best {best_score:.4f}"]
            })

        # 4. Financials
        fee_usd  = round((best.fee_pct / 100) * req.amount_usd + best.flat_fee_usd, 4)
        fee_pct  = round((fee_usd / req.amount_usd) * 100, 4)
        received = round(req.amount_usd - fee_usd, 4)

        return RouteDecision(
            selected_provider=best,
            total_fee_usd=fee_usd,
            fee_pct_effective=fee_pct,
            estimated_received_usd=received,
            settlement_minutes=best.settlement_minutes,
            score=best_score,
            rejected_providers=rejected,
            compliance_passed=True,
            compliance_notes=notes,
        )


# ─── Exceptions ───────────────────────────────────────────────────────────────

class ComplianceError(Exception):
    def __init__(self, msg: str, notes: list):
        super().__init__(msg)
        self.notes = notes

class NoRouteError(Exception):
    def __init__(self, msg: str, rejected: list):
        super().__init__(msg)
        self.rejected = rejected
