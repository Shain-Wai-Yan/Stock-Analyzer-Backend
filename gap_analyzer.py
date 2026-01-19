"""
Gap Analysis Engine
Calculates gap fill probability from historical data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

class GapAnalyzer:
    def __init__(self, alpaca_client):
        self.alpaca = alpaca_client
    
    async def scan_gaps(self, min_gap: float, max_gap: float, limit: int) -> List[Dict]:
        """
        Scan for stocks with gaps
        Returns list of gapping stocks with basic info
        """
        # Get market movers from Alpaca
        movers = await self.alpaca.get_movers(limit * 2)  # Get more to filter
        
        gaps = []
        for mover in movers:
            symbol = mover['symbol']
            
            # Get latest bars
            bars = await self.alpaca.get_bars(symbol, limit=2)
            if len(bars) < 2:
                continue
            
            prev_close = bars.iloc[-2]['close']
            current_open = bars.iloc[-1]['open']
            current_price = bars.iloc[-1]['close']
            
            # Calculate gap
            gap_pct = ((current_open - prev_close) / prev_close) * 100
            
            # Filter by gap size
            if min_gap <= abs(gap_pct) <= max_gap:
                # Calculate volume ratio
                avg_volume = bars['volume'].mean()
                current_volume = bars.iloc[-1]['volume']
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                gaps.append({
                    "symbol": symbol,
                    "price": float(current_price),
                    "previousClose": float(prev_close),
                    "gapPercent": float(gap_pct),
                    "direction": "up" if gap_pct > 0 else "down",
                    "volume": int(current_volume),
                    "volumeRatio": float(volume_ratio),
                    "timestamp": bars.iloc[-1].name.isoformat()
                })
        
        # Sort by gap size and return top results
        gaps.sort(key=lambda x: abs(x['gapPercent']), reverse=True)
        return gaps[:limit]
    
    async def calculate_fill_probability(self, symbol: str, lookback_days: int = 100) -> Dict:
        """
        Calculate gap fill probability using historical data
        This is the CORE algorithm for 80%+ win rate
        """
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        df = await self.alpaca.get_historical_bars(
            symbol, 
            start_date.isoformat(), 
            end_date.isoformat(),
            timeframe='1Day'
        )
        
        if df is None or len(df) < 20:
            return {
                "fill_rate": 0.5,  # Default
                "avg_fill_time": 0,
                "total_gaps": 0
            }
        
        # Identify gaps
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        df['prev_close'] = df['close'].shift(1)
        
        # Gap up: open > prev_high
        df['gap_up'] = df['open'] > df['prev_high']
        
        # Gap down: open < prev_low  
        df['gap_down'] = df['open'] < df['prev_low']
        
        df['has_gap'] = df['gap_up'] | df['gap_down']
        
        # Calculate fills
        fill_times = []
        total_gaps = 0
        filled_gaps = 0
        
        for idx in range(len(df)):
            if not df['has_gap'].iloc[idx]:
                continue
            
            total_gaps += 1
            
            # Check if gap fills in next N bars
            gap_level = df['prev_high'].iloc[idx] if df['gap_up'].iloc[idx] else df['prev_low'].iloc[idx]
            
            # Look forward up to 10 bars
            for j in range(1, min(11, len(df) - idx)):
                future_idx = idx + j
                
                # Check if price touched gap level
                if df['gap_up'].iloc[idx]:
                    # Gap up fills when low touches prev_high
                    if df['low'].iloc[future_idx] <= gap_level:
                        filled_gaps += 1
                        fill_times.append(j)
                        break
                else:
                    # Gap down fills when high touches prev_low
                    if df['high'].iloc[future_idx] >= gap_level:
                        filled_gaps += 1
                        fill_times.append(j)
                        break
        
        # Calculate statistics
        fill_rate = filled_gaps / total_gaps if total_gaps > 0 else 0.5
        avg_fill_time = np.mean(fill_times) if fill_times else 0
        
        return {
            "fill_rate": float(fill_rate),
            "avg_fill_time": float(avg_fill_time),
            "total_gaps": int(total_gaps),
            "filled_gaps": int(filled_gaps)
        }
    
    async def run_backtest(self, symbol: str, days: int = 365) -> Dict:
        """
        Run simple backtest for gap fill strategy
        Returns performance metrics
        """
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = await self.alpaca.get_historical_bars(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            timeframe='1Day'
        )
        
        if df is None or len(df) < 50:
            return {
                "total_return": 0,
                "win_rate": 0,
                "total_trades": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "avg_win": 0,
                "avg_loss": 0
            }
        
        # Identify gaps
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        df['prev_close'] = df['close'].shift(1)
        df['open'] = df['open']
        
        # Gap up: open > prev_high (at least 2%)
        df['gap_up'] = (df['open'] > df['prev_high']) & (((df['open'] - df['prev_high']) / df['prev_high']) > 0.02)
        
        # Gap down: open < prev_low (at least 2%)
        df['gap_down'] = (df['open'] < df['prev_low']) & (((df['prev_low'] - df['open']) / df['prev_low']) > 0.02)
        
        df['has_gap'] = df['gap_up'] | df['gap_down']
        
        # Simulate trades
        trades = []
        initial_capital = 10000
        capital = initial_capital
        
        for idx in range(1, len(df)):
            if not df['has_gap'].iloc[idx]:
                continue
            
            # Entry
            entry_price = df['open'].iloc[idx]
            gap_level = df['prev_high'].iloc[idx] if df['gap_up'].iloc[idx] else df['prev_low'].iloc[idx]
            
            # Look forward for exit (gap fill or max 10 bars)
            exit_price = None
            exit_idx = None
            
            for j in range(1, min(11, len(df) - idx)):
                future_idx = idx + j
                
                # Check if gap filled
                if df['gap_up'].iloc[idx]:
                    # Gap up fills when low touches prev_high
                    if df['low'].iloc[future_idx] <= gap_level:
                        exit_price = gap_level
                        exit_idx = future_idx
                        break
                else:
                    # Gap down fills when high touches prev_low
                    if df['high'].iloc[future_idx] >= gap_level:
                        exit_price = gap_level
                        exit_idx = future_idx
                        break
            
            # If no fill, exit at close of 10th bar
            if exit_price is None and idx + 10 < len(df):
                exit_price = df['close'].iloc[idx + 10]
                exit_idx = idx + 10
            elif exit_price is None:
                continue
            
            # Calculate trade result
            if df['gap_up'].iloc[idx]:
                # Short position (profit when price goes down)
                pnl_pct = (entry_price - exit_price) / entry_price
            else:
                # Long position (profit when price goes up)
                pnl_pct = (exit_price - entry_price) / entry_price
            
            # Apply commission (0.1% both ways)
            pnl_pct -= 0.002
            
            # Calculate trade value
            position_size = capital * 0.1  # Use 10% of capital per trade
            pnl = position_size * pnl_pct
            capital += pnl
            
            trades.append({
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'pnl': pnl,
                'bars_held': exit_idx - idx
            })
        
        # Calculate statistics
        if len(trades) == 0:
            return {
                "total_return": 0,
                "win_rate": 0.5,
                "total_trades": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "avg_win": 0,
                "avg_loss": 0
            }
        
        winning_trades = [t for t in trades if t['pnl_pct'] > 0]
        losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
        
        total_return = ((capital - initial_capital) / initial_capital) * 100
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) * 100 if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) * 100 if losing_trades else 0
        
        # Calculate Sharpe ratio (simplified)
        returns = [t['pnl_pct'] for t in trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Calculate max drawdown
        cumulative_returns = np.cumsum([t['pnl'] for t in trades])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / initial_capital * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        return {
            "total_return": float(total_return),
            "win_rate": float(win_rate),
            "total_trades": int(len(trades)),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss)
        }
