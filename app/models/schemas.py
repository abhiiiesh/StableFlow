from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum
import uuid


# ─── Payment Schemas ─────────────────────────────────────────────────────────

class CreatePaymentIntent(BaseModel):
    merchant_id: str
    amount: float = Field(..., gt=0)
    token: Literal["USDT", "USDC"] = "USDT"
    currency: str = "USD"
    description: Optional[str] = None
    customer_email: Optional[str] = None
    metadata: Optional[dict] = None


class PaymentIntent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    merchant_id: str
    amount: float
    token: str
    status: Literal["pending", "confirming", "completed", "failed", "expired"] = "pending"
    payment_address: str
    description: Optional[str] = None
    customer_email: Optional[str] = None
    metadata: Optional[dict] = None
    tx_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class ConfirmPayment(BaseModel):
    tx_hash: str


class TransactionStatus(BaseModel):
    tx_hash: str
    status: Literal["pending", "success", "failed"]
    confirmations: int
    block_number: Optional[int] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    value: Optional[float] = None


# ─── Merchant Schemas ─────────────────────────────────────────────────────────

class MerchantCreate(BaseModel):
    name: str
    email: str
    wallet_address: str
    webhook_url: Optional[str] = None


class Merchant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    wallet_address: str
    webhook_url: Optional[str] = None
    api_key: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", ""))
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Webhook Schemas ──────────────────────────────────────────────────────────

class WebhookEvent(BaseModel):
    event: str
    payment_id: str
    status: str
    tx_hash: Optional[str] = None
    amount: float
    token: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Routing Schemas ──────────────────────────────────────────────────────────

class RoutingStrategy(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST  = "fastest"
    BALANCED = "balanced"


class RouteRequestBody(BaseModel):
    sender_country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    receiver_country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    amount_usd: float = Field(..., gt=0)
    token: Literal["USDT", "USDC"] = "USDT"
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    user_kyc_level: int = Field(1, ge=0, le=2)
    include_explanation: bool = True
