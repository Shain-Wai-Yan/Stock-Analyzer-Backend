"""
Alpaca Markets API Client
FREE tier - IEX data feed
"""
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, List, Dict

class AlpacaClient:
    def __init__(self):
        # Get from environment or use paper trading keys
        self.api_key = os.getenv('ALPACA_API_KEY', 'YOUR_ALPACA_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET', 'YOUR_ALPACA_SECRET')
        
        # Initialize clients
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.trading_client = TradingClient(self.api_key, self.api_secret, paper=True)
    
    async def get_movers(self, limit: int = 50) -> List[Dict]:
        """
        Get market movers (stocks with significant movement)
        Uses Alpaca's screener
        """
        try:
            # Get most active stocks
            # Note: Free tier has limited screener access
            # We'll use a predefined list of liquid stocks
            liquid_stocks = [
                'AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META',
                'AMD', 'NFLX', 'DIS', 'BA', 'GE', 'F', 'INTC', 'SNAP',
                'UBER', 'LYFT', 'COIN', 'SQ', 'PYPL', 'SHOP', 'RBLX',
                'PLTR', 'SOFI', 'NIO', 'RIVN', 'LCID', 'PLUG', 'SPCE',
                'GME', 'AMC', 'BB', 'WISH', 'CLOV', 'BBIG', 'PROG'
            ]
            
            # Get snapshots for these stocks
            movers = []
            for symbol in liquid_stocks[:limit]:
                try:
                    snapshot = self.data_client.get_stock_snapshot(
                        StockSnapshotRequest(symbol_or_symbols=symbol)
                    )
                    
                    if symbol in snapshot:
                        snap = snapshot[symbol]
                        movers.append({
                            'symbol': symbol,
                            'price': float(snap.latest_trade.price),
                            'change_pct': float(snap.daily_bar.change_percent) if snap.daily_bar else 0
                        })
                except:
                    continue
            
            return movers
            
        except Exception as e:
            print(f"Error getting movers: {e}")
            return []
    
    async def get_bars(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Get recent bar data for a symbol"""
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                limit=limit
            )
            
            bars = self.data_client.get_stock_bars(request)
            df = bars.df
            
            if not df.empty and 'symbol' in df.index.names:
                df = df.reset_index(level='symbol', drop=True)
            
            return df
            
        except Exception as e:
            print(f"Error getting bars for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_historical_bars(
        self, 
        symbol: str, 
        start: str, 
        end: str,
        timeframe: str = '1Day'
    ) -> Optional[pd.DataFrame]:
        """Get historical bar data"""
        try:
            # Convert timeframe
            if timeframe == '1Day':
                tf = TimeFrame.Day
            elif timeframe == '1Hour':
                tf = TimeFrame.Hour
            else:
                tf = TimeFrame.Day
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=datetime.fromisoformat(start.replace('Z', '+00:00')),
                end=datetime.fromisoformat(end.replace('Z', '+00:00'))
            )
            
            bars = self.data_client.get_stock_bars(request)
            df = bars.df
            
            if not df.empty and 'symbol' in df.index.names:
                df = df.reset_index(level='symbol', drop=True)
            
            return df
            
        except Exception as e:
            print(f"Error getting historical bars for {symbol}: {e}")
            return None
    
    async def get_latest_quote(self, symbol: str) -> Dict:
        """Get latest quote for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)
            
            if symbol in quote:
                q = quote[symbol]
                return {
                    "symbol": symbol,
                    "bid": float(q.bid_price),
                    "ask": float(q.ask_price),
                    "bid_size": int(q.bid_size),
                    "ask_size": int(q.ask_size),
                    "timestamp": q.timestamp.isoformat()
                }
            
            return {}
            
        except Exception as e:
            print(f"Error getting quote for {symbol}: {e}")
            return {}
    
    async def get_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get news for a symbol"""
        try:
            # Note: Alpaca's free tier has limited news access
            # You might need to use alternative free news sources
            news = []
            
            # Placeholder - integrate free news API here
            # Examples: News API, Alpha Vantage, Yahoo Finance
            
            return news
            
        except Exception as e:
            print(f"Error getting news for {symbol}: {e}")
            return []
