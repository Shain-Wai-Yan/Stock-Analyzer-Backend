"""Database models and schemas"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

Base = declarative_base()


# SQLAlchemy Models
class GapScanResult(Base):
    """Store gap scan results for historical analysis"""
    __tablename__ = "gap_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    scan_date = Column(DateTime, default=func.now(), index=True)
    gap_percent = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    volume_ratio = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=True)
    conviction = Column(String(10), nullable=True)
    filled = Column(Boolean, default=False)
    fill_date = Column(DateTime, nullable=True)
    fill_hours = Column(Float, nullable=True)


class Trade(Base):
    """Store trade journal entries"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    entry_date = Column(DateTime, default=func.now())
    entry_price = Column(Float, nullable=False)
    exit_date = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=False)  # long/short
    reason = Column(Text, nullable=True)
    outcome = Column(String(20), nullable=True)  # win/loss/breakeven
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


class Alert(Base):
    """Store price alerts"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    alert_type = Column(String(20), nullable=False)  # gap, price, volume
    condition = Column(String(10), nullable=False)  # >, <, =
    value = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    triggered_at = Column(DateTime, nullable=True)


# Pydantic Schemas for API
class GapDataResponse(BaseModel):
    """Gap data response schema matching frontend expectations"""
    symbol: str
    name: str
    gapPercent: float = Field(alias="gap_percent")
    currentPrice: float = Field(alias="current_price")
    previousClose: float = Field(alias="previous_close")
    volume: int
    volumeRatio: float = Field(alias="volume_ratio")
    sentimentScore: float = Field(default=0.5, alias="sentiment_score")
    historicalFillRate: int = Field(default=65, alias="historical_fill_rate")
    conviction: str = Field(default="medium")
    sector: str = Field(default="Technology")
    marketCap: str = Field(default="Large", alias="market_cap")
    preMarketHigh: float = Field(alias="premarket_high")
    preMarketLow: float = Field(alias="premarket_low")
    vwap: float = Field(default=0.0)
    lastUpdated: str = Field(alias="last_updated")
    
    class Config:
        populate_by_name = True


class NewsItemResponse(BaseModel):
    """News item response schema"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    publishedAt: str = Field(alias="published_at")
    sentiment: float = Field(default=0.5)
    relatedSymbols: List[str] = Field(default_factory=list, alias="related_symbols")
    
    class Config:
        populate_by_name = True


class BacktestResultResponse(BaseModel):
    """Backtest result response schema"""
    symbol: str
    startDate: str = Field(alias="start_date")
    endDate: str = Field(alias="end_date")
    totalTrades: int = Field(alias="total_trades")
    winRate: float = Field(alias="win_rate")
    avgWin: float = Field(alias="avg_win")
    avgLoss: float = Field(alias="avg_loss")
    maxDrawdown: float = Field(alias="max_drawdown")
    sharpeRatio: float = Field(alias="sharpe_ratio")
    totalReturn: float = Field(alias="total_return")
    
    class Config:
        populate_by_name = True


class ChartDataResponse(BaseModel):
    """Chart data response schema"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class TradeJournalEntry(BaseModel):
    """Trade journal entry schema"""
    symbol: str
    reason: str
    entry: float
    stop: float
    target: float
    quantity: Optional[int] = None


class StrategyStatus(BaseModel):
    """Strategy engine status"""
    running: bool
    mode: str
    positions: int
    cash: float
    portfolio_value: float
    daily_pnl: float
    win_rate: float
