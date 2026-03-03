from fastapi import APIRouter, Request, HTTPException, Header
import hmac
import hashlib
from app.core.config import settings

router = APIRouter()


@router.post("/test-receiver")
async def test_webhook_receiver(
    request: Request,
    x_stableflow_signature: str = Header(None),
):
    """Demo endpoint to test webhook delivery with HMAC signature validation."""
    body = await request.body()

    if x_stableflow_signature:
        expected = "sha256=" + hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_stableflow_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return {"received": True, "payload": await request.json()}
