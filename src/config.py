from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (SQLite by default, Postgres via docker-compose)
    DATABASE_URL: str = "sqlite:///polymarket_insider.db"

    # Ingestion: Polymarket's public trades API, no key needed
    TRADES_API_URL: str = "https://data-api.polymarket.com/trades"
    POLL_INTERVAL_SECONDS: float = 5.0

    # Scoring
    ANOMALY_THRESHOLD: float = 60.0
    LARGE_TRADE_USD: float = 10_000.0

    # Isolation Forest retraining
    MIN_TRAINING_TRADES: int = 1_000
    RETRAIN_INTERVAL_SECONDS: int = 3_600

    # Notifications (Discord webhooks, optional)
    WEBHOOK_URL: str = ""
    ALL_TRADES_WEBHOOK_URL: str = ""


settings = Settings()
