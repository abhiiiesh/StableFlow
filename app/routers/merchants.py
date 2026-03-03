from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import MerchantCreate, Merchant
from app.db.models import MerchantModel
from app.db.database import get_db
import uuid

router = APIRouter()


@router.post("/register", response_model=Merchant, status_code=201)
async def register_merchant(data: MerchantCreate, db: AsyncSession = Depends(get_db)):
    """Register a new merchant and receive an API key."""
    row = MerchantModel(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        wallet_address=data.wallet_address,
        webhook_url=data.webhook_url,
        api_key=str(uuid.uuid4()).replace("-", ""),
    )
    db.add(row)
    await db.flush()
    return Merchant(
        id=row.id, name=row.name, email=row.email,
        wallet_address=row.wallet_address, webhook_url=row.webhook_url,
        api_key=row.api_key, created_at=row.created_at,
    )


@router.get("/{merchant_id}", response_model=Merchant)
async def get_merchant(merchant_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MerchantModel).where(MerchantModel.id == merchant_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return Merchant(
        id=row.id, name=row.name, email=row.email,
        wallet_address=row.wallet_address, webhook_url=row.webhook_url,
        api_key=row.api_key, created_at=row.created_at,
    )
