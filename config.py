"""Configuration management using pydantic-settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Keys
    alpaca_api_key: str
    alpaca_secret_key: str
    groq_api_key: Optional[str] = None
    
    # Alpaca Configuration
    alpaca_paper: bool = True
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    
    # Trading Configuration
    max_position_size: float = 10000.0  # Max $ per position
    max_portfolio_risk: float = 0.02  # 2% max risk per trade
    gap_min_percent: float = 2.0  # Minimum gap % to consider
    gap_max_percent: float = 15.0  # Maximum gap % (too high = risky)
    volume_ratio_min: float = 1.5  # Minimum volume ratio
    sentiment_threshold: float = 0.5  # Minimum sentiment score
    
    # Strategy Settings
    strategy_mode: str = "paper"  # paper, backtest, live
    enable_live_trading: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./gap_scanner.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # Monitoring
    enable_metrics: bool = True
    
    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
