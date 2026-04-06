import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://polymarket:password@localhost:5432/polymarket_insider"
    
    # Blockchain
    POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
    POLYGON_WSS_URL: str = os.getenv("POLYGON_WSS_URL", "wss://polygon-rpc.com/ws")
    POLYMARKET_CTF_ADDRESS: str = "0x4D97DCd97eC945f40CF65F87097ACe5EA0476045" # Example CTF Contract
    
    # ML & Scoring
    ANOMALY_THRESHOLD: float = 80.0
    
    # Notifications
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "") # Discord or Telegram

    class Config:
        env_file = ".env"

settings = Settings()