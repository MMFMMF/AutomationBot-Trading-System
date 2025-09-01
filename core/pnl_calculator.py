"""
Real-time P&L Calculator with Market Data Integration
Fixes all P&L calculation and performance metric issues
"""
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from core.config_manager import SystemConfig
from providers.base_providers import PriceDataProvider

logger = logging.getLogger(__name__)

@dataclass
class PositionPnL:
    """Individual position P&L calculation"""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    entry_price: float
    current_price: float
    entry_time: datetime
    unrealized_pnl: float
    unrealized_pnl_percent: float
    market_value: float
    cost_basis: float
    last_price_update: datetime
    trade_ids: List[str]  # All trades contributing to this position

@dataclass
class PerformanceMetrics:
    """Real performance metrics calculated from actual trades"""
    total_trades: int
    open_trades: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    max_drawdown_percent: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    last_updated: datetime

class RealTimePnLCalculator:
    """
    Real-time P&L calculator that fixes all calculation issues:
    1. Real-time unrealized P&L calculations
    2. Accurate win rate from closed trades only
    3. Position-level P&L tracking
    4. Comprehensive performance metrics
    5. Market price integration
    """
    
    def __init__(self, config: SystemConfig, price_provider: Optional[PriceDataProvider] = None):
        self.config = config
        self.price_provider = price_provider
        self.database_path = config.database_path
        self.positions_cache: Dict[str, PositionPnL] = {}
        self.performance_cache: Optional[PerformanceMetrics] = None
        self.last_price_update = datetime.now()
        self.price_update_interval = 30  # seconds
        
        # Initialize database
        self._init_database()
        
        logger.info("Real-time P&L calculator initialized")
    
    def _init_database(self):
        """Initialize database tables for P&L tracking"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create P&L tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS position_pnl (
                    symbol TEXT,
                    side TEXT,
                    quantity REAL,
                    entry_price REAL,
                    current_price REAL,
                    unrealized_pnl REAL,
                    market_value REAL,
                    cost_basis REAL,
                    last_updated TIMESTAMP,
                    trade_ids TEXT,
                    PRIMARY KEY (symbol, side)
                )
            ''')
            
            # Create performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_name TEXT PRIMARY KEY,
                    metric_value REAL,
                    last_updated TIMESTAMP
                )
            ''')
            
            # Create price history table for accurate P&L tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    symbol TEXT,
                    price REAL,
                    timestamp TIMESTAMP,
                    source TEXT,
                    PRIMARY KEY (symbol, timestamp)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("P&L database tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize P&L database: {e}")
            raise
    
    async def update_market_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Update current market prices for all symbols
        """
        current_prices = {}
        
        if not self.price_provider:
            logger.warning("No price provider available - using simulated prices")
            return current_prices
        
        try:
            for symbol in symbols:
                try:
                    # Get current market price
                    price_data = await self.price_provider.get_current_price(symbol)
                    if price_data and 'price' in price_data:
                        current_prices[symbol] = float(price_data['price'])
                        
                        # Store price in history
                        self._store_price_history(symbol, current_prices[symbol], 'market_data')
                        
                        logger.debug(f"Updated price for {symbol}: ${current_prices[symbol]:.4f}")
                    else:
                        logger.warning(f"No price data available for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Failed to get price for {symbol}: {e}")
                    continue
            
            self.last_price_update = datetime.now()
            logger.info(f"Updated prices for {len(current_prices)} symbols")
            
        except Exception as e:
            logger.error(f"Error updating market prices: {e}")
        
        return current_prices
    
    def _store_price_history(self, symbol: str, price: float, source: str):
        """Store price data for audit trail"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO price_history (symbol, price, timestamp, source)
                VALUES (?, ?, ?, ?)
            ''', (symbol, price, datetime.now(), source))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store price history for {symbol}: {e}")
    
    def calculate_position_pnl(self, trades_data: List[Dict]) -> Dict[str, PositionPnL]:
        """
        Calculate P&L for all positions with real-time market prices
        """
        positions = {}
        current_prices = {}
        
        # Group trades by symbol and side to create positions
        position_groups = {}
        for trade in trades_data:
            if trade.get('status') != 'open':
                continue
                
            symbol = trade['symbol']
            side = trade['side']
            key = f"{symbol}_{side}"
            
            if key not in position_groups:
                position_groups[key] = {
                    'symbol': symbol,
                    'side': side,
                    'trades': []
                }
            position_groups[key]['trades'].append(trade)
        
        # Get current market prices for all symbols
        symbols = list(set(trade['symbol'] for trade in trades_data if trade.get('status') == 'open'))
        if symbols:
            try:
                # Try to get real-time prices
                asyncio.create_task(self.update_market_prices(symbols))
                current_prices = self._get_latest_prices(symbols)
            except Exception as e:
                logger.error(f"Failed to get current prices: {e}")
                current_prices = {}
        
        # Calculate P&L for each position
        for key, position_group in position_groups.items():
            symbol = position_group['symbol']
            side = position_group['side']
            trades = position_group['trades']
            
            if not trades:
                continue
            
            # Calculate position metrics
            total_quantity = sum(float(trade.get('quantity', 0)) for trade in trades)
            total_cost = sum(float(trade.get('quantity', 0)) * float(trade.get('entry_price', 0)) for trade in trades)
            
            if total_quantity == 0:
                continue
                
            avg_entry_price = total_cost / total_quantity
            
            # Get current market price
            current_price = current_prices.get(symbol)
            if current_price is None:
                # Use last known price or entry price as fallback
                current_price = self._get_fallback_price(symbol, avg_entry_price)
                logger.warning(f"Using fallback price for {symbol}: ${current_price:.4f}")
            
            # Calculate P&L based on position side
            if side.lower() == 'buy':
                # Long position: profit when current price > entry price
                unrealized_pnl = (current_price - avg_entry_price) * total_quantity
                market_value = current_price * total_quantity
            else:
                # Short position: profit when current price < entry price  
                unrealized_pnl = (avg_entry_price - current_price) * total_quantity
                market_value = current_price * total_quantity
            
            unrealized_pnl_percent = (unrealized_pnl / total_cost) * 100 if total_cost > 0 else 0
            
            # Create position P&L object
            position_pnl = PositionPnL(
                symbol=symbol,
                side=side,
                quantity=total_quantity,
                entry_price=avg_entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                market_value=market_value,
                cost_basis=total_cost,
                last_price_update=datetime.now(),
                trade_ids=[trade.get('trade_id', '') for trade in trades],
                entry_time=min(datetime.fromisoformat(trade.get('entry_time', datetime.now().isoformat())) for trade in trades)
            )
            
            positions[key] = position_pnl
            
            # Log P&L calculation details
            logger.debug(f"""
            Position P&L Calculation for {symbol} {side}:
            - Quantity: {total_quantity}
            - Entry Price: ${avg_entry_price:.4f}
            - Current Price: ${current_price:.4f}
            - Cost Basis: ${total_cost:.2f}
            - Market Value: ${market_value:.2f}
            - Unrealized P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_percent:.2f}%)
            """)
        
        self.positions_cache = positions
        self._store_position_pnl(positions)
        
        return positions
    
    def _get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices from database or cache"""
        prices = {}
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            for symbol in symbols:
                cursor.execute('''
                    SELECT price FROM price_history 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (symbol,))
                
                result = cursor.fetchone()
                if result:
                    prices[symbol] = result[0]
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to get latest prices: {e}")
        
        return prices
    
    def _get_fallback_price(self, symbol: str, default_price: float) -> float:
        """Get fallback price when market data is unavailable"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get last known price from history
            cursor.execute('''
                SELECT price FROM price_history 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
                
        except Exception as e:
            logger.error(f"Failed to get fallback price for {symbol}: {e}")
        
        return default_price
    
    def _store_position_pnl(self, positions: Dict[str, PositionPnL]):
        """Store position P&L data in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            for key, position in positions.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO position_pnl 
                    (symbol, side, quantity, entry_price, current_price, unrealized_pnl, 
                     market_value, cost_basis, last_updated, trade_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.symbol,
                    position.side,
                    position.quantity,
                    position.entry_price,
                    position.current_price,
                    position.unrealized_pnl,
                    position.market_value,
                    position.cost_basis,
                    position.last_price_update,
                    json.dumps(position.trade_ids)
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored P&L data for {len(positions)} positions")
            
        except Exception as e:
            logger.error(f"Failed to store position P&L: {e}")
    
    def calculate_performance_metrics(self, all_trades: List[Dict]) -> PerformanceMetrics:
        """
        Calculate accurate performance metrics from trade data
        """
        now = datetime.now()
        
        # Separate open and closed trades
        open_trades = [t for t in all_trades if t.get('status') == 'open']
        closed_trades = [t for t in all_trades if t.get('status') == 'closed' and t.get('pnl') is not None]
        
        # Basic counts
        total_trades = len(all_trades)
        open_count = len(open_trades)
        closed_count = len(closed_trades)
        
        # Calculate realized P&L from closed trades only
        realized_pnl = sum(float(trade.get('pnl', 0)) for trade in closed_trades)
        
        # Calculate unrealized P&L from positions
        positions = self.calculate_position_pnl(open_trades)
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions.values())
        
        total_pnl = realized_pnl + unrealized_pnl
        
        # Win/Loss analysis (from closed trades only)
        winning_trades = [t for t in closed_trades if float(t.get('pnl', 0)) > 0]
        losing_trades = [t for t in closed_trades if float(t.get('pnl', 0)) < 0]
        
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        # Win rate calculation
        if closed_count > 0:
            win_rate = (winning_count / closed_count) * 100
        else:
            win_rate = 0.0  # No closed trades yet
        
        # Profit/Loss calculations
        gross_profit = sum(float(t.get('pnl', 0)) for t in winning_trades)
        gross_loss = abs(sum(float(t.get('pnl', 0)) for t in losing_trades))
        
        # Profit factor
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0.0
        
        # Average win/loss
        average_win = gross_profit / winning_count if winning_count > 0 else 0.0
        average_loss = gross_loss / losing_count if losing_count > 0 else 0.0
        
        # Largest win/loss
        largest_win = max((float(t.get('pnl', 0)) for t in winning_trades), default=0.0)
        largest_loss = min((float(t.get('pnl', 0)) for t in losing_trades), default=0.0)
        
        # Consecutive wins/losses (simplified)
        consecutive_wins = self._calculate_consecutive_wins(closed_trades)
        consecutive_losses = self._calculate_consecutive_losses(closed_trades)
        
        # Max drawdown calculation
        max_drawdown, max_drawdown_percent = self._calculate_max_drawdown(closed_trades)
        
        # Sharpe ratio (requires return history - simplified for now)
        sharpe_ratio = self._calculate_sharpe_ratio(closed_trades) if closed_count > 5 else None
        
        metrics = PerformanceMetrics(
            total_trades=total_trades,
            open_trades=open_count,
            closed_trades=closed_count,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            last_updated=now
        )
        
        self.performance_cache = metrics
        self._store_performance_metrics(metrics)
        
        # Log performance calculation details
        logger.info(f"""
        Performance Metrics Calculated:
        - Total Trades: {total_trades} (Open: {open_count}, Closed: {closed_count})
        - Win Rate: {win_rate:.1f}% ({winning_count}/{closed_count} closed trades)
        - Total P&L: ${total_pnl:.2f} (Realized: ${realized_pnl:.2f}, Unrealized: ${unrealized_pnl:.2f})
        - Profit Factor: {profit_factor:.2f}
        - Max Drawdown: ${max_drawdown:.2f} ({max_drawdown_percent:.1f}%)
        """)
        
        return metrics
    
    def _calculate_consecutive_wins(self, closed_trades: List[Dict]) -> int:
        """Calculate current consecutive wins"""
        if not closed_trades:
            return 0
        
        # Sort by exit time
        sorted_trades = sorted(closed_trades, key=lambda x: x.get('exit_time', ''))
        consecutive = 0
        
        for trade in reversed(sorted_trades):
            pnl = float(trade.get('pnl', 0))
            if pnl > 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _calculate_consecutive_losses(self, closed_trades: List[Dict]) -> int:
        """Calculate current consecutive losses"""
        if not closed_trades:
            return 0
        
        # Sort by exit time
        sorted_trades = sorted(closed_trades, key=lambda x: x.get('exit_time', ''))
        consecutive = 0
        
        for trade in reversed(sorted_trades):
            pnl = float(trade.get('pnl', 0))
            if pnl < 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _calculate_max_drawdown(self, closed_trades: List[Dict]) -> Tuple[float, float]:
        """Calculate maximum drawdown from closed trades"""
        if not closed_trades:
            return 0.0, 0.0
        
        # Sort trades by exit time
        sorted_trades = sorted(closed_trades, key=lambda x: x.get('exit_time', ''))
        
        running_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in sorted_trades:
            pnl = float(trade.get('pnl', 0))
            running_pnl += pnl
            
            if running_pnl > peak:
                peak = running_pnl
            
            drawdown = peak - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        max_drawdown_percent = (max_drawdown / peak * 100) if peak > 0 else 0.0
        
        return max_drawdown, max_drawdown_percent
    
    def _calculate_sharpe_ratio(self, closed_trades: List[Dict]) -> Optional[float]:
        """Calculate simplified Sharpe ratio"""
        if len(closed_trades) < 5:
            return None
        
        try:
            # Calculate daily returns
            daily_returns = []
            for trade in closed_trades:
                pnl = float(trade.get('pnl', 0))
                # Simplified daily return calculation
                daily_returns.append(pnl)
            
            if not daily_returns:
                return None
            
            # Calculate mean and standard deviation
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            std_dev = variance ** 0.5
            
            if std_dev == 0:
                return None
            
            # Simplified Sharpe ratio (assuming risk-free rate = 0)
            sharpe_ratio = mean_return / std_dev
            
            return sharpe_ratio
            
        except Exception as e:
            logger.error(f"Failed to calculate Sharpe ratio: {e}")
            return None
    
    def _store_performance_metrics(self, metrics: PerformanceMetrics):
        """Store performance metrics in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Store each metric as a separate row
            metrics_dict = asdict(metrics)
            
            for key, value in metrics_dict.items():
                if value is not None:
                    cursor.execute('''
                        INSERT OR REPLACE INTO performance_metrics 
                        (metric_name, metric_value, last_updated)
                        VALUES (?, ?, ?)
                    ''', (key, float(value) if isinstance(value, (int, float)) else str(value), datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.debug("Stored performance metrics in database")
            
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get comprehensive position summary with P&L"""
        if not self.positions_cache:
            return {
                "total_positions": 0,
                "total_unrealized_pnl": 0.0,
                "positions": [],
                "last_updated": datetime.now().isoformat()
            }
        
        positions_list = []
        total_unrealized = 0.0
        
        for position in self.positions_cache.values():
            position_data = {
                "symbol": position.symbol,
                "side": position.side,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_percent": position.unrealized_pnl_percent,
                "market_value": position.market_value,
                "cost_basis": position.cost_basis,
                "last_price_update": position.last_price_update.isoformat(),
                "trade_count": len(position.trade_ids)
            }
            positions_list.append(position_data)
            total_unrealized += position.unrealized_pnl
        
        return {
            "total_positions": len(self.positions_cache),
            "total_unrealized_pnl": total_unrealized,
            "positions": sorted(positions_list, key=lambda x: abs(x["unrealized_pnl"]), reverse=True),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.performance_cache:
            return {
                "status": "No performance data available",
                "last_updated": datetime.now().isoformat()
            }
        
        metrics = self.performance_cache
        
        return {
            "trading_summary": {
                "total_trades": metrics.total_trades,
                "open_trades": metrics.open_trades,
                "closed_trades": metrics.closed_trades,
                "win_rate": f"{metrics.win_rate:.1f}%" if metrics.closed_trades > 0 else "No closed trades",
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades
            },
            "pnl_summary": {
                "total_pnl": f"${metrics.total_pnl:.2f}",
                "realized_pnl": f"${metrics.realized_pnl:.2f}",
                "unrealized_pnl": f"${metrics.unrealized_pnl:.2f}",
                "gross_profit": f"${metrics.gross_profit:.2f}",
                "gross_loss": f"${metrics.gross_loss:.2f}",
                "profit_factor": f"{metrics.profit_factor:.2f}" if metrics.profit_factor != float('inf') else "Undefined"
            },
            "risk_metrics": {
                "max_drawdown": f"${metrics.max_drawdown:.2f}",
                "max_drawdown_percent": f"{metrics.max_drawdown_percent:.1f}%",
                "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio is not None else "Calculating...",
                "average_win": f"${metrics.average_win:.2f}",
                "average_loss": f"${metrics.average_loss:.2f}",
                "largest_win": f"${metrics.largest_win:.2f}",
                "largest_loss": f"${metrics.largest_loss:.2f}"
            },
            "streaks": {
                "consecutive_wins": metrics.consecutive_wins,
                "consecutive_losses": metrics.consecutive_losses
            },
            "last_updated": metrics.last_updated.isoformat()
        }


def get_pnl_calculator(config: SystemConfig, price_provider: Optional[PriceDataProvider] = None) -> RealTimePnLCalculator:
    """Factory function to get P&L calculator instance"""
    return RealTimePnLCalculator(config, price_provider)