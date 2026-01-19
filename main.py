"""FastAPI application - Bridge between frontend and Lumibot strategy"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import sys
from typing import List

# Local imports
from config import settings
from database import init_db, close_db, get_db
from models import (
    GapDataResponse,
    NewsItemResponse,
    BacktestResultResponse,
    ChartDataResponse,
    TradeJournalEntry,
    StrategyStatus,
    Trade,
)
from data_service import get_market_gaps, get_chart_data, get_account_info, get_positions
from sentiment_service import get_news_sentiment, get_gap_reason
from backtest_service import run_backtest

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Gap Scanner API...")
    
    # Initialize database
    await init_db()
    
    # TODO: Initialize Lumibot strategy in background thread
    # For now, strategy runs separately
    logger.info("API ready. Strategy can be started separately.")
    
    yield
    
    # Cleanup
    await close_db()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Gap Scanner API",
    description="Professional gap trading backend with Lumibot + OpenBB + FastAPI",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Gap Scanner API",
        "version": "2.0.0",
        "mode": settings.strategy_mode,
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        account = await get_account_info()
        return {
            "status": "healthy",
            "database": "connected",
            "alpaca": "connected" if account else "error",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            },
        )


@app.get("/api/gaps", response_model=List[GapDataResponse])
async def get_gaps():
    """
    Get current market gaps
    
    Returns list of stocks with significant gaps
    """
    try:
        gaps = await get_market_gaps()
        return gaps
    except Exception as e:
        logger.error(f"Error in /api/gaps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gaps/{symbol}", response_model=GapDataResponse)
async def get_gap_details(symbol: str):
    """Get detailed gap information for a specific symbol"""
    try:
        gaps = await get_market_gaps()
        gap = next((g for g in gaps if g["symbol"] == symbol), None)
        
        if not gap:
            raise HTTPException(status_code=404, detail=f"Gap not found for {symbol}")
        
        return gap
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/gaps/{symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chart/{symbol}", response_model=List[ChartDataResponse])
async def get_chart(symbol: str, timeframe: str = "1D"):
    """
    Get chart data for a symbol
    
    Timeframes: 1M, 5M, 15M, 1H, 1D
    """
    try:
        chart_data = await get_chart_data(symbol, timeframe)
        return chart_data
    except Exception as e:
        logger.error(f"Error in /api/chart/{symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news", response_model=List[NewsItemResponse])
async def get_news(symbol: str = None):
    """
    Get market news
    
    If symbol provided, returns symbol-specific news
    """
    try:
        if symbol:
            news = await get_news_sentiment(symbol)
        else:
            # Return general market news
            news = []
        
        return news
    except Exception as e:
        logger.error(f"Error in /api/news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gap-reason/{symbol}")
async def get_gap_reasoning(symbol: str):
    """
    Get AI-generated explanation for why a gap occurred
    """
    try:
        # First get the gap data
        gaps = await get_market_gaps()
        gap = next((g for g in gaps if g["symbol"] == symbol), None)
        
        if not gap:
            raise HTTPException(status_code=404, detail=f"Gap not found for {symbol}")
        
        # Get AI reasoning
        reason = await get_gap_reason(symbol, gap["gap_percent"])
        return reason
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/gap-reason/{symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/{symbol}", response_model=BacktestResultResponse)
async def backtest_symbol(symbol: str, days: int = 90):
    """
    Run backtest for gap strategy on a symbol
    
    days: Number of days to backtest (default 90)
    """
    try:
        result = await run_backtest(symbol, days)
        return result
    except Exception as e:
        logger.error(f"Error in /api/backtest/{symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status", response_model=StrategyStatus)
async def get_strategy_status():
    """
    Get current strategy status and statistics
    """
    try:
        account = await get_account_info()
        positions = await get_positions()
        
        return {
            "running": True,  # Will integrate with actual strategy later
            "mode": settings.strategy_mode,
            "positions": len(positions),
            "cash": account.get("cash", 0.0),
            "portfolio_value": account.get("portfolio_value", 0.0),
            "daily_pnl": 0.0,  # Calculate from positions
            "win_rate": 0.0,  # Will come from database
        }
    except Exception as e:
        logger.error(f"Error in /api/status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trades")
async def save_trade(trade: TradeJournalEntry, db: AsyncSession = Depends(get_db)):
    """Save a trade to the journal"""
    try:
        db_trade = Trade(
            symbol=trade.symbol,
            entry_price=trade.entry,
            quantity=trade.quantity or 100,
            direction="long",
            reason=trade.reason,
        )
        db.add(db_trade)
        await db.commit()
        
        return {"status": "success", "trade_id": db_trade.id}
        
    except Exception as e:
        logger.error(f"Error saving trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades")
async def get_trades(db: AsyncSession = Depends(get_db)):
    """Get trade journal entries"""
    try:
        from sqlalchemy import select
        
        result = await db.execute(select(Trade).order_by(Trade.entry_date.desc()).limit(50))
        trades = result.scalars().all()
        
        return [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "entryDate": t.entry_date.isoformat(),
                "entryPrice": t.entry_price,
                "exitDate": t.exit_date.isoformat() if t.exit_date else None,
                "exitPrice": t.exit_price,
                "quantity": t.quantity,
                "direction": t.direction,
                "reason": t.reason,
                "outcome": t.outcome,
                "pnl": t.pnl,
                "pnlPercent": t.pnl_percent,
                "notes": t.notes,
            }
            for t in trades
        ]
        
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions")
async def get_current_positions():
    """Get current open positions"""
    try:
        positions = await get_positions()
        return positions
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account")
async def get_account():
    """Get account information"""
    try:
        account = await get_account_info()
        return account
    except Exception as e:
        logger.error(f"Error fetching account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Add datetime import
from datetime import datetime


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )
