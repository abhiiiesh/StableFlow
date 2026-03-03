"""
ORM Models — replaces in-memory dicts with persistent PostgreSQL tables.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PaymentIntentModel(Base):
    __tablename__ = "payment_intents"

    id:              Mapped[str]   = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id:     Mapped[str]   = mapped_column(String(36), index=True, nullable=False)
    amount:          Mapped[float] = mapped_column(Float, nullable=False)
    token:           Mapped[str]   = mapped_column(String(10), nullable=False)
    status:          Mapped[str]   = mapped_column(String(20), default="pending", nullable=False)
    payment_address: Mapped[str]   = mapped_column(String(42), nullable=False)
    description:     Mapped[str]   = mapped_column(Text, nullable=True)
    customer_email:  Mapped[str]   = mapped_column(String(255), nullable=True)
    meta:            Mapped[dict]  = mapped_column(JSON, nullable=True)
    tx_hash:         Mapped[str]   = mapped_column(String(66), nullable=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at:      Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MerchantModel(Base):
    __tablename__ = "merchants"

    id:              Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name:            Mapped[str] = mapped_column(String(255), nullable=False)
    email:           Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    wallet_address:  Mapped[str] = mapped_column(String(42), nullable=False)
    webhook_url:     Mapped[str] = mapped_column(String(500), nullable=True)
    api_key:         Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at:      Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
