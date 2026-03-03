from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import CreatePaymentIntent, PaymentIntent, ConfirmPayment, WebhookEvent
from app.services import payment_service
from app.services.webhook_service import send_webhook
from app.db.database import get_db

router = APIRouter()


@router.post("/intent", response_model=PaymentIntent, status_code=201)
async def create_payment(data: CreatePaymentIntent, db: AsyncSession = Depends(get_db)):
    """Create a payment intent. Returns payment_address and payment ID."""
    return await payment_service.create_payment_intent(data, db)


@router.get("/{payment_id}", response_model=PaymentIntent)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    """Poll payment intent status."""
    intent = await payment_service.get_payment_intent(payment_id, db)
    if not intent:
        raise HTTPException(status_code=404, detail="Payment not found")
    return intent


@router.post("/{payment_id}/confirm", response_model=PaymentIntent)
async def confirm_payment(
    payment_id: str,
    body: ConfirmPayment,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit tx_hash. Verifies on BNB Chain and fires webhook on completion."""
    try:
        intent = await payment_service.confirm_payment(payment_id, body.tx_hash, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if intent.status in ("completed", "failed"):
        merchant = await payment_service.get_merchant_by_id(intent.merchant_id, db)
        if merchant and merchant.webhook_url:
            event = WebhookEvent(
                event=f"payment.{intent.status}",
                payment_id=intent.id,
                status=intent.status,
                tx_hash=intent.tx_hash,
                amount=intent.amount,
                token=intent.token,
            )
            background_tasks.add_task(send_webhook, merchant.webhook_url, event)

    return intent


@router.get("/merchant/{merchant_id}", response_model=list[PaymentIntent])
async def list_merchant_payments(merchant_id: str, db: AsyncSession = Depends(get_db)):
    """List all payments for a merchant."""
    return await payment_service.list_payments(merchant_id, db)
