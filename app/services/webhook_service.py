import httpx
import hmac
import hashlib
import logging
from datetime import datetime
from app.models.schemas import WebhookEvent
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_webhook(webhook_url: str, event: WebhookEvent) -> bool:
    payload = event.model_dump_json()
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-StableFlow-Signature": f"sha256={signature}",
        "X-StableFlow-Timestamp": datetime.utcnow().isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, content=payload, headers=headers)
            if resp.status_code == 200:
                logger.info("Webhook delivered to %s for event %s", webhook_url, event.event)
                return True
            logger.warning("Webhook to %s returned %s", webhook_url, resp.status_code)
            return False
    except Exception as e:
        logger.error("Webhook delivery failed: %s", e)
        return False
