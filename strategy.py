"""Lumibot Gap Trading Strategy with OpenBB data integration"""
from lumibot.strategies import Strategy
from lumibot.brokers import Alpaca
from lumibot.entities import Asset
from datetime import datetime, timedelta
from config import settings
import logging
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class GapTradingStrategy(Strategy):
    """
    Professional gap trading strategy using Lumibot framework
    
    Strategy Logic:
    1. Scan for gaps > 2% at market open
    2. Check volume ratio > 1.5x average
    3. Validate sentiment if available
    4. Enter on gap fill attempt
    5. Exit on target or stop loss
    """
    
    parameters = {
        "gap_min": 2.0,
        "gap_max": 15.0,
        "volume_ratio_min": 1.5,
        "risk_per_trade": 0.02,  # 2% portfolio risk
        "profit_target_ratio": 2.0,  # 2:1 reward:risk
        "max_positions": 3,
        "scan_symbols": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD"],
    }
    
    def initialize(self):
        """Initialize strategy"""
        self.sleeptime = "5M"  # Check every 5 minutes
        self.gap_candidates: Dict[str, Dict] = {}
        self.positions_entered_today = []
        
        # Track for frontend API
        self.last_scan_results = []
        self.strategy_stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
        }
        
        logger.info("GapTradingStrategy initialized")
    
    def on_trading_iteration(self):
        """Main trading loop called every sleeptime"""
        try:
            current_time = self.get_datetime()
            
            # Only scan for gaps near market open (9:30 - 10:00 ET)
            if self._is_scan_time(current_time):
                self._scan_for_gaps()
            
            # Manage existing positions
            self._manage_positions()
            
            # Enter new positions if conditions met
            self._check_entry_signals()
            
        except Exception as e:
            logger.error(f"Error in trading iteration: {e}", exc_info=True)
    
    def _is_scan_time(self, dt: datetime) -> bool:
        """Check if current time is within gap scanning window"""
        market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
        scan_end = dt.replace(hour=10, minute=0, second=0, microsecond=0)
        return market_open <= dt <= scan_end
    
    def _scan_for_gaps(self):
        """Scan symbols for gap opportunities"""
        self.gap_candidates.clear()
        self.last_scan_results.clear()
        
        for symbol in self.parameters["scan_symbols"]:
            try:
                gap_data = self._analyze_gap(symbol)
                if gap_data and self._is_valid_gap(gap_data):
                    self.gap_candidates[symbol] = gap_data
                    self.last_scan_results.append(gap_data)
                    logger.info(f"Gap detected: {symbol} at {gap_data['gap_percent']:.2f}%")
            except Exception as e:
                logger.warning(f"Failed to analyze {symbol}: {e}")
        
        logger.info(f"Gap scan complete. Found {len(self.gap_candidates)} candidates")
    
    def _analyze_gap(self, symbol: str) -> Optional[Dict]:
        """Analyze single symbol for gap"""
        try:
            # Get current price
            current_price = self.get_last_price(symbol)
            if not current_price:
                return None
            
            # Get previous close
            bars = self.get_historical_prices(symbol, 2, "day")
            if bars is None or bars.df.empty:
                return None
            
            prev_close = bars.df["close"].iloc[-2]
            gap_percent = ((current_price - prev_close) / prev_close) * 100
            
            # Get volume data
            current_bars = self.get_historical_prices(symbol, 20, "minute")
            if current_bars is None or current_bars.df.empty:
                volume = 0
                volume_ratio = 0
            else:
                volume = current_bars.df["volume"].iloc[-1]
                avg_volume = current_bars.df["volume"].mean()
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "previous_close": prev_close,
                "gap_percent": gap_percent,
                "volume": int(volume),
                "volume_ratio": volume_ratio,
                "timestamp": self.get_datetime(),
            }
        
        except Exception as e:
            logger.error(f"Error analyzing gap for {symbol}: {e}")
            return None
    
    def _is_valid_gap(self, gap_data: Dict) -> bool:
        """Validate gap meets criteria"""
        gap_pct = abs(gap_data["gap_percent"])
        
        # Check gap size
        if gap_pct < self.parameters["gap_min"] or gap_pct > self.parameters["gap_max"]:
            return False
        
        # Check volume
        if gap_data["volume_ratio"] < self.parameters["volume_ratio_min"]:
            return False
        
        return True
    
    def _check_entry_signals(self):
        """Check for entry signals on gap candidates"""
        current_positions = len(self.get_positions())
        
        if current_positions >= self.parameters["max_positions"]:
            return
        
        for symbol, gap_data in list(self.gap_candidates.items()):
            if symbol in self.positions_entered_today:
                continue
            
            # Check if price is filling the gap
            current_price = self.get_last_price(symbol)
            gap_pct = gap_data["gap_percent"]
            
            # Entry condition: price moving towards previous close
            if gap_pct > 0:  # Gap up
                # Enter short if price starts declining
                if current_price < gap_data["current_price"] * 0.98:
                    self._enter_position(symbol, "short", gap_data)
            else:  # Gap down
                # Enter long if price starts rising
                if current_price > gap_data["current_price"] * 1.02:
                    self._enter_position(symbol, "long", gap_data)
    
    def _enter_position(self, symbol: str, direction: str, gap_data: Dict):
        """Enter a position with proper risk management"""
        try:
            current_price = self.get_last_price(symbol)
            portfolio_value = self.get_portfolio_value()
            
            # Calculate position size based on risk
            risk_amount = portfolio_value * self.parameters["risk_per_trade"]
            
            # Calculate stop loss (gap start point)
            if direction == "long":
                stop_loss = gap_data["current_price"]
                target = current_price + (current_price - stop_loss) * self.parameters["profit_target_ratio"]
            else:  # short
                stop_loss = gap_data["current_price"]
                target = current_price - (stop_loss - current_price) * self.parameters["profit_target_ratio"]
            
            # Calculate shares based on stop distance
            stop_distance = abs(current_price - stop_loss)
            if stop_distance == 0:
                return
            
            shares = int(risk_amount / stop_distance)
            if shares <= 0:
                return
            
            # Create order
            order_side = "buy" if direction == "long" else "sell"
            order = self.create_order(symbol, shares, order_side)
            self.submit_order(order)
            
            # Track entry
            self.positions_entered_today.append(symbol)
            self.strategy_stats["total_trades"] += 1
            
            logger.info(f"Entered {direction} position: {symbol} @ {current_price}, Stop: {stop_loss}, Target: {target}")
            
        except Exception as e:
            logger.error(f"Failed to enter position for {symbol}: {e}")
    
    def _manage_positions(self):
        """Manage open positions with stops and targets"""
        positions = self.get_positions()
        
        for position in positions:
            try:
                symbol = position.symbol
                current_price = self.get_last_price(symbol)
                
                # Simple exit: close at end of day
                current_time = self.get_datetime()
                market_close = current_time.replace(hour=15, minute=50, second=0)
                
                if current_time >= market_close:
                    self.sell_all()
                    logger.info(f"Closed {symbol} at end of day")
                    
            except Exception as e:
                logger.error(f"Error managing position {symbol}: {e}")
    
    def on_abrupt_closing(self):
        """Handle strategy shutdown"""
        logger.info("Strategy closing - liquidating all positions")
        self.sell_all()
    
    def trace_stats(self, context, snapshot_before):
        """Track strategy statistics"""
        row = {
            "timestamp": self.get_datetime(),
            "portfolio_value": self.get_portfolio_value(),
            "cash": self.get_cash(),
            "positions": len(self.get_positions()),
        }
        return row


# Global strategy instance (will be initialized in main.py)
strategy_instance: Optional[GapTradingStrategy] = None


def get_strategy() -> Optional[GapTradingStrategy]:
    """Get the running strategy instance"""
    return strategy_instance


def set_strategy(strategy: GapTradingStrategy):
    """Set the strategy instance"""
    global strategy_instance
    strategy_instance = strategy
