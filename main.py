"""
StableFlow — AI-Powered Stablecoin Payment Rails on BNB Chain
Unified entry point: Payment API + AI Routing Engine
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import payments, merchants, webhooks, routing
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations on startup."""
    await init_db()
    yield


app = FastAPI(
    title="StableFlow API",
    description="AI-Powered Stablecoin Payment Rails on BNB Chain",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments.router,  prefix="/api/v1/payments",  tags=["Payments"])
app.include_router(merchants.router, prefix="/api/v1/merchants", tags=["Merchants"])
app.include_router(webhooks.router,  prefix="/api/v1/webhooks",  tags=["Webhooks"])
app.include_router(routing.router,   prefix="/api/v1/routing",   tags=["AI Routing"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "project": "StableFlow",
        "version": "1.0.0",
        "chain": "BNB Chain",
        "modules": ["payments", "merchants", "webhooks", "ai-routing"],
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
