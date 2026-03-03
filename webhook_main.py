"""
StableFlow — Webhook Service (standalone)
Exposes the webhook test receiver and handles delivery status.
Shares the PostgreSQL DB with the Payment API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import webhooks
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="StableFlow Webhook Service",
    description="HMAC-signed webhook delivery for merchant payment events",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "webhook-service"}
