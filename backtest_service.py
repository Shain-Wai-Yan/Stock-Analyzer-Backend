"""Backtesting service using Lumibot"""
from lumibot.backtesting import YahooDataBacktesting
from strategy import GapTradingStrategy
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)


async def run_backtest(symbol: str, days: int = 90) -> Dict:
    """
    Run backtest for gap strategy on a symbol
    
    Note: This is a simplified backtest. In production, you'd want
    more sophisticated backtesting with proper data sources.
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Create strategy instance for backtesting
        GapTradingStrategy.parameters["scan_symbols"] = [symbol]
        
        # Run backtest using Yahoo data (free)
        results = GapTradingStrategy.backtest(
            YahooDataBacktesting,
            start_date,
            end_date,
            parameters={
                "scan_symbols": [symbol],
            },
        )
        
        # Extract metrics
        if results and hasattr(results, "get"):
            total_return = results.get("total_return", 0.0)
            total_trades = results.get("total_trades", 0)
            win_rate = results.get("win_rate", 0.0)
            sharpe = results.get("sharpe_ratio", 0.0)
            max_dd = results.get("max_drawdown", 0.0)
            avg_win = results.get("avg_win", 0.0)
            avg_loss = results.get("avg_loss", 0.0)
        else:
            # Default values if backtest fails
            total_return = 0.0
            total_trades = 0
            win_rate = 0.0
            sharpe = 0.0
            max_dd = 0.0
            avg_win = 0.0
            avg_loss = 0.0
        
        return {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_trades": total_trades,
            "win_rate": round(win_rate * 100, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_return": round(total_return * 100, 2),
        }
        
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        
        # Return default data on error
        return {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "total_return": 0.0,
        }
