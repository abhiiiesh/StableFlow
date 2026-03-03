"""
Payment Service — PostgreSQL-backed (replaces in-memory dict store).
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import CreatePaymentIntent, PaymentIntent, TransactionStatus
from app.db.models import PaymentIntentModel, MerchantModel
from app.core.bnb_client import get_web3, get_token_contract, STABLECOIN_CONTRACTS
from app.core.config import settings


def _orm_to_schema(row: PaymentIntentModel) -> PaymentIntent:
    return PaymentIntent(
        id=row.id, merchant_id=row.merchant_id, amount=row.amount,
        token=row.token, status=row.status, payment_address=row.payment_address,
        description=row.description, customer_email=row.customer_email,
        metadata=row.meta, tx_hash=row.tx_hash,
        created_at=row.created_at, expires_at=row.expires_at,
    )


async def create_payment_intent(data: CreatePaymentIntent, db: AsyncSession) -> PaymentIntent:
    row = PaymentIntentModel(
        id=str(uuid.uuid4()), merchant_id=data.merchant_id,
        amount=data.amount, token=data.token, status="pending",
        payment_address=settings.MERCHANT_WALLET_ADDRESS,
        description=data.description, customer_email=data.customer_email,
        meta=data.metadata, created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(row)
    await db.flush()
    return _orm_to_schema(row)


async def get_payment_intent(payment_id: str, db: AsyncSession) -> Optional[PaymentIntent]:
    result = await db.execute(select(PaymentIntentModel).where(PaymentIntentModel.id == payment_id))
    row = result.scalar_one_or_none()
    return _orm_to_schema(row) if row else None


async def confirm_payment(payment_id: str, tx_hash: str, db: AsyncSession) -> PaymentIntent:
    result = await db.execute(select(PaymentIntentModel).where(PaymentIntentModel.id == payment_id))
    row = result.scalar_one_or_none()
    if not row:
        raise ValueError("Payment intent not found")
    if row.status == "completed":
        return _orm_to_schema(row)

    tx_status = await verify_transaction(tx_hash, row.token, row.amount)
    if tx_status.status == "success":
        row.status = "completed"; row.tx_hash = tx_hash
    elif tx_status.status == "pending":
        row.status = "confirming"; row.tx_hash = tx_hash
    else:
        row.status = "failed"
    await db.flush()
    return _orm_to_schema(row)


async def list_payments(merchant_id: str, db: AsyncSession) -> list[PaymentIntent]:
    result = await db.execute(
        select(PaymentIntentModel)
        .where(PaymentIntentModel.merchant_id == merchant_id)
        .order_by(PaymentIntentModel.created_at.desc())
    )
    return [_orm_to_schema(row) for row in result.scalars().all()]


async def get_merchant_by_id(merchant_id: str, db: AsyncSession) -> Optional[MerchantModel]:
    result = await db.execute(select(MerchantModel).where(MerchantModel.id == merchant_id))
    return result.scalar_one_or_none()


async def verify_transaction(tx_hash: str, token: str, expected_amount: float) -> TransactionStatus:
    w3 = get_web3()
    try:
        tx      = w3.eth.get_transaction(tx_hash)
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        latest  = w3.eth.block_number
        confirmations = latest - receipt.blockNumber if receipt else 0
        contract = get_token_contract(token)
        decimals = contract.functions.decimals().call()
        transferred = 0.0
        if receipt and receipt.logs:
            for log in receipt.logs:
                if log.address.lower() == STABLECOIN_CONTRACTS[token].lower():
                    try:
                        decoded = contract.events.Transfer().process_log(log)
                        transferred = decoded["args"]["value"] / (10 ** decimals)
                    except Exception:
                        pass
        status = "pending"
        if receipt:
            status = "success" if receipt.status == 1 and confirmations >= 3 else \
                     "failed"  if receipt.status == 0 else "pending"
        return TransactionStatus(
            tx_hash=tx_hash, status=status, confirmations=confirmations,
            block_number=receipt.blockNumber if receipt else None,
            from_address=tx["from"], to_address=tx.get("to"), value=transferred,
        )
    except Exception:
        return TransactionStatus(
            tx_hash=tx_hash, status="pending", confirmations=0,
            block_number=None, from_address=None, to_address=None, value=None,
        )
