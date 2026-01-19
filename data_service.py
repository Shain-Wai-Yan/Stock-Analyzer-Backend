"""Data fetching service using OpenBB SDK and Alpaca"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Alpaca clients with IEX feed (works with free tier)
stock_client = StockHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    raw_data=False,
    url_override=None,
)

trading_client = TradingClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    paper=settings.alpaca_paper,
)


async def get_market_gaps() -> List[Dict]:
    """
    Scan for market gaps using Alpaca data
    This is optimized to work within free tier limits
    """
    gaps = []
    
    # Watchlist of most active stocks
    symbols = [
        "SPY", "QQQ", "IWM", "DIA",  # ETFs
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD",  # Mega caps
        "NFLX", "BABA", "COIN", "PLTR", "SOFI", "MARA", "RIOT",  # High volatility
    ]
    
    try:
        # Get previous close
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        for symbol in symbols:
            try:
                # Get historical bars using IEX feed (free tier compatible)
                request_params = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    feed="iex",  # Use IEX feed instead of SIP for free tier
                )
                bars = stock_client.get_stock_bars(request_params)
                
                if not bars or symbol not in bars:
                    continue
                
                bars_df = bars[symbol].df
                if len(bars_df) < 2:
                    continue
                
                prev_close = bars_df["close"].iloc[-2]
                
                # Get current price using IEX feed
                quote_request = StockLatestQuoteRequest(
                    symbol_or_symbols=symbol,
                    feed="iex"  # Use IEX feed for free tier
                )
                quote = stock_client.get_stock_latest_quote(quote_request)
                
                if symbol not in quote:
                    continue
                
                current_price = float(quote[symbol].ask_price or quote[symbol].bid_price or prev_close)
                
                # Calculate gap
                gap_percent = ((current_price - prev_close) / prev_close) * 100
                
                # Only include significant gaps
                if abs(gap_percent) < 1.5:
                    continue
                
                # Calculate volume metrics
                current_volume = int(bars_df["volume"].iloc[-1])
                avg_volume = int(bars_df["volume"].mean())
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                # Get premarket high/low (approximate from current data)
                premarket_high = current_price * 1.005
                premarket_low = current_price * 0.995
                
                gap_data = {
                    "symbol": symbol,
                    "name": symbol,  # Would need separate API for company names
                    "gap_percent": round(gap_percent, 2),
                    "current_price": round(current_price, 2),
                    "previous_close": round(prev_close, 2),
                    "volume": current_volume,
                    "volume_ratio": round(volume_ratio, 2),
                    "sentiment_score": 0.5,  # Default, can be enhanced with news
                    "historical_fill_rate": 65,  # Would calculate from historical data
                    "conviction": _calculate_conviction(gap_percent, volume_ratio),
                    "sector": "Technology",  # Would need separate data source
                    "market_cap": "Large",
                    "premarket_high": round(premarket_high, 2),
                    "premarket_low": round(premarket_low, 2),
                    "vwap": round(bars_df["vwap"].iloc[-1] if "vwap" in bars_df else current_price, 2),
                    "last_updated": datetime.now().isoformat(),
                }
                
                gaps.append(gap_data)
                logger.info(f"Gap detected: {symbol} at {gap_percent:.2f}%")
                
            except Exception as e:
                logger.warning(f"Failed to process {symbol}: {e}")
                continue
        
        # Sort by absolute gap percent
        gaps.sort(key=lambda x: abs(x["gap_percent"]), reverse=True)
        
        logger.info(f"Found {len(gaps)} gaps")
        return gaps
        
    except Exception as e:
        logger.error(f"Error scanning for gaps: {e}", exc_info=True)
        return []


def _calculate_conviction(gap_percent: float, volume_ratio: float) -> str:
    """Calculate conviction level based on gap metrics"""
    score = 0
    
    # Gap size scoring
    if abs(gap_percent) > 5:
        score += 2
    elif abs(gap_percent) > 3:
        score += 1
    
    # Volume scoring
    if volume_ratio > 3:
        score += 2
    elif volume_ratio > 2:
        score += 1
    
    # Determine conviction
    if score >= 3:
        return "high"
    elif score >= 2:
        return "medium"
    else:
        return "low"


async def get_chart_data(symbol: str, timeframe: str = "1D") -> List[Dict]:
    """Get chart data for a symbol"""
    try:
        # Map timeframe string to Alpaca TimeFrame
        tf_map = {
            "1M": TimeFrame.Minute,
            "5M": TimeFrame(5, "Min"),
            "15M": TimeFrame(15, "Min"),
            "1H": TimeFrame.Hour,
            "1D": TimeFrame.Day,
        }
        
        alpaca_tf = tf_map.get(timeframe, TimeFrame.Day)
        
        # Calculate date range
        days = 1 if "M" in timeframe or "H" in timeframe else 30
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start_date,
            end=end_date,
            feed="iex",  # Use IEX feed for free tier
        )
        
        bars = stock_client.get_stock_bars(request_params)
        
        if not bars or symbol not in bars:
            return []
        
        bars_df = bars[symbol].df
        
        # Convert to chart format
        chart_data = []
        for idx, row in bars_df.iterrows():
            chart_data.append({
                "time": idx.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            })
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        return []


async def get_account_info() -> Dict:
    """Get trading account information"""
    try:
        account = trading_client.get_account()
        return {
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "day_trade_count": int(account.daytrade_count),
        }
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        return {}


async def get_positions() -> List[Dict]:
    """Get current positions"""
    try:
        positions = trading_client.get_all_positions()
        return [
            {
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "market_value": float(pos.market_value),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc),
            }
            for pos in positions
        ]
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return []
