"""
StableFlow — Full Test Suite
Tests: Payment API, Routing Engine, Compliance, Webhooks
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.services.routing_engine import (
    RoutingEngine, RouteRequest, RoutingStrategy, ComplianceError, NoRouteError
)

engine = RoutingEngine()

# ─── Routing Engine Unit Tests ────────────────────────────────────────────────

class TestRoutingEngine:

    def test_binance_p2p_us_to_in(self):
        req = RouteRequest(sender_country="US", receiver_country="IN", amount_usd=500, token="USDT")
        d = engine.route(req)
        assert d.selected_provider.provider == "Binance P2P"
        assert d.total_fee_usd == 0.0
        assert d.estimated_received_usd == 500.0
        assert d.compliance_passed is True

    def test_zero_fee_on_binance_p2p(self):
        req = RouteRequest(sender_country="SG", receiver_country="IN", amount_usd=1000)
        d = engine.route(req)
        assert d.total_fee_usd == 0.0
        assert d.fee_pct_effective == 0.0

    def test_cheapest_strategy(self):
        req = RouteRequest(sender_country="US", receiver_country="IN", amount_usd=200,
                           strategy=RoutingStrategy.CHEAPEST)
        d = engine.route(req)
        assert d.selected_provider.provider == "Binance P2P"

    def test_unsupported_corridor_falls_back(self):
        # US→JP not in Binance P2P corridors — should fall back to Transak/MoonPay
        req = RouteRequest(sender_country="US", receiver_country="JP", amount_usd=100)
        d = engine.route(req)
        assert d.selected_provider.provider != "Binance P2P"

    def test_audit_trail_populated(self):
        req = RouteRequest(sender_country="US", receiver_country="IN", amount_usd=250)
        d = engine.route(req)
        assert isinstance(d.rejected_providers, list)
        assert d.score > 0
        assert len(d.rejected_providers) > 0  # other providers were considered

    def test_ctr_threshold_noted_not_blocked(self):
        req = RouteRequest(sender_country="US", receiver_country="IN",
                           amount_usd=12_000, user_kyc_level=2)
        d = engine.route(req)
        assert any("CTR" in n for n in d.compliance_notes)
        assert d.compliance_passed is True


class TestComplianceEngine:

    def test_blocks_sanctioned_receiver(self):
        req = RouteRequest(sender_country="US", receiver_country="IR", amount_usd=100)
        with pytest.raises(ComplianceError) as exc:
            engine.route(req)
        assert "BLOCKED" in exc.value.notes[0]

    def test_blocks_sanctioned_sender(self):
        req = RouteRequest(sender_country="KP", receiver_country="IN", amount_usd=100)
        with pytest.raises(ComplianceError):
            engine.route(req)

    def test_blocks_insufficient_kyc_for_large_amount(self):
        req = RouteRequest(sender_country="US", receiver_country="IN",
                           amount_usd=5_000, user_kyc_level=1)
        with pytest.raises(ComplianceError) as exc:
            engine.route(req)
        assert any("KYC" in n for n in exc.value.notes)

    def test_high_risk_country_flags_edd(self):
        req = RouteRequest(sender_country="US", receiver_country="AF",
                           amount_usd=100, user_kyc_level=2)
        d = engine.route(req)
        assert any("EDD" in n for n in d.compliance_notes)


class TestNoRouteError:

    def test_amount_below_all_minimums(self):
        req = RouteRequest(sender_country="US", receiver_country="IN", amount_usd=1.0)
        with pytest.raises(NoRouteError) as exc:
            engine.route(req)
        assert len(exc.value.rejected) > 0


# ─── API Integration Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestPaymentAPI:

    async def test_register_merchant_and_create_intent(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            merchant_res = await client.post("/api/v1/merchants/register", json={
                "name": "TestMerchant", "email": "test@merchant.com",
                "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
            })
            assert merchant_res.status_code == 201
            merchant = merchant_res.json()
            assert "api_key" in merchant

            intent_res = await client.post("/api/v1/payments/intent", json={
                "merchant_id": merchant["id"],
                "amount": 50.00,
                "token": "USDT",
                "description": "Test order",
            })
            assert intent_res.status_code == 201
            intent = intent_res.json()
            assert intent["status"] == "pending"
            assert intent["amount"] == 50.0
            assert "payment_address" in intent
            assert "expires_at" in intent

    async def test_get_payment_not_found(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/payments/nonexistent-id")
            assert res.status_code == 404

    async def test_list_merchant_payments(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/payments/merchant/any-id")
            assert res.status_code == 200
            assert isinstance(res.json(), list)


@pytest.mark.asyncio
class TestRoutingAPI:

    async def test_route_us_to_in(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/api/v1/routing/route", json={
                "sender_country": "US",
                "receiver_country": "IN",
                "amount_usd": 300,
                "token": "USDT",
                "strategy": "balanced",
                "include_explanation": False,
            })
            assert res.status_code == 200
            data = res.json()
            assert data["route"]["provider"] == "Binance P2P"
            assert data["financials"]["total_fee_usd"] == 0.0
            assert data["compliance"]["passed"] is True

    async def test_route_compliance_block(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/api/v1/routing/route", json={
                "sender_country": "US",
                "receiver_country": "IR",
                "amount_usd": 100,
            })
            assert res.status_code == 451
            assert res.json()["detail"]["error"] == "COMPLIANCE_BLOCKED"

    async def test_list_corridors(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/routing/corridors")
            assert res.status_code == 200
            data = res.json()
            assert data["provider"] == "Binance P2P"
            assert data["total"] > 0

    async def test_health(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/health")
            assert res.status_code == 200
            assert res.json()["status"] == "ok"
