"""
StableFlow — Routing Engine Service (standalone)
Deployed independently from the Payment API — no DB dependency.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import routing

app = FastAPI(
    title="StableFlow Routing Engine",
    description="AI-Powered Cross-Border Stablecoin Route Optimizer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routing.router, prefix="/api/v1/routing", tags=["AI Routing"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "routing-engine"}
