from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # BNB Chain
    BNB_RPC_URL: str = "https://bsc-dataseed.binance.org/"
    MERCHANT_PRIVATE_KEY: str = ""
    MERCHANT_WALLET_ADDRESS: str = "0x0000000000000000000000000000000000000000"

    # Stablecoin contracts (BEP-20, BNB Chain Mainnet)
    USDT_CONTRACT: str = "0x55d398326f99059fF775485246999027B3197955"
    USDC_CONTRACT: str = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"

    # App
    SECRET_KEY: str = "dev-secret-change-in-production"
    WEBHOOK_SECRET: str = "webhook-secret-change-in-production"

    # Database — Render injects DATABASE_URL automatically for attached Postgres
    # asyncpg is used in production; aiosqlite for local dev fallback
    DATABASE_URL: str = "sqlite+aiosqlite:///./stableflow.db"

    # AI
    ANTHROPIC_API_KEY: str = ""

    # Service identity (used in logs and health checks)
    SERVICE_NAME: str = "stableflow-api"

    @property
    def async_database_url(self) -> str:
        """
        Render provides postgresql:// — SQLAlchemy async needs postgresql+asyncpg://
        Also handles sqlite for local dev.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            # Render legacy format
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url  # sqlite+aiosqlite — local dev

    class Config:
        env_file = ".env"


settings = Settings()
