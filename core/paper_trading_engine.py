import logging
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import json
import random
from pathlib import Path
import math

from core.models import TradingSignal, OrderSide, OrderType, SignalStatus
from core.execution_mode_manager import ExecutionModeManager
from providers.base_providers import PriceDataProvider

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    MOVING_AVERAGE_CROSSOVER = "ma_crossover"
    RSI_MEAN_REVERSION = "rsi_mean_reversion"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    MEAN_REVERSION = "mean_reversion"

class SignalStrength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class PaperTrade:
    trade_id: str
    signal_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    fees: float = 0.0
    slippage: float = 0.0
    strategy: str = ""
    mode: str = ""
    status: str = "open"
    metadata: Dict[str, Any] = None

@dataclass
class StrategyPerformance:
    strategy_name: str
    total_signals: int = 0
    executed_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    last_updated: datetime = None

class PaperTradingEngine:
    """Comprehensive paper trading engine with automated strategy execution"""
    
    def __init__(self, automation_engine, execution_mode_manager: ExecutionModeManager):
        self.automation_engine = automation_engine
        self.execution_mode_manager = execution_mode_manager
        
        # Trading state
        self.is_running = False
        self.paper_trades: Dict[str, PaperTrade] = {}
        self.open_positions: Dict[str, PaperTrade] = {}
        self.strategy_performances: Dict[str, StrategyPerformance] = {}
        
        # Configuration
        self.trading_config = self._load_trading_config()
        self.market_hours = self._get_market_hours()
        
        # Signal generation
        self.last_signal_time = {}
        self.price_history: Dict[str, List[Dict]] = {}
        self.strategy_states: Dict[str, Dict] = {}
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.total_trades = 0
        self.system_start_time = datetime.now()
        
        # Initialize strategies
        self._initialize_strategies()
        
        logger.info("Paper trading engine initialized")
    
    def _load_trading_config(self) -> Dict[str, Any]:
        """Load paper trading configuration"""
        config_path = Path("./config/paper_trading_config.json")
        
        default_config = {
            "signal_generation": {
                "enabled": True,
                "interval_minutes": 15,
                "strategies_enabled": ["ma_crossover", "rsi_mean_reversion", "momentum_breakout"],
                "max_signals_per_hour": 12,
                "min_signal_strength": "moderate"
            },
            "execution": {
                "slippage": {
                    "stocks": 0.02,  # 0.02%
                    "crypto": 0.15,  # 0.15%
                    "etfs": 0.01     # 0.01%
                },
                "fees": {
                    "tradestation": 0.50,  # $0.50 per trade
                    "defi": 25.0           # ~$25 average gas cost
                },
                "partial_fills": 0.05,  # 5% chance of partial fill
                "rejection_rate": 0.02  # 2% chance of rejection
            },
            "risk_management": {
                "max_position_size_pct": 8.0,  # 8% of portfolio per position
                "stop_loss_pct": 3.0,          # 3% stop loss
                "take_profit_pct": 6.0,        # 6% take profit
                "max_daily_trades": 20,
                "max_positions": 10
            },
            "symbols": {
                "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"],
                "crypto": ["ETH", "BTC", "USDC"],
                "etfs": ["SPY", "QQQ", "IWM", "VTI"]
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            else:
                # Save default config
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
        except Exception as e:
            logger.error(f"Error loading trading config: {e}")
            return default_config
    
    def _get_market_hours(self) -> Dict[str, Any]:
        """Get market hours for different asset classes"""
        return {
            "stocks": {
                "open": "09:30",
                "close": "16:00",
                "timezone": "US/Eastern"
            },
            "crypto": {
                "open": "00:00", 
                "close": "23:59",
                "timezone": "UTC"
            },
            "etfs": {
                "open": "09:30",
                "close": "16:00", 
                "timezone": "US/Eastern"
            }
        }
    
    def _initialize_strategies(self):
        """Initialize all trading strategies"""
        strategies = ["ma_crossover", "rsi_mean_reversion", "momentum_breakout"]
        
        for strategy in strategies:
            self.strategy_performances[strategy] = StrategyPerformance(
                strategy_name=strategy,
                last_updated=datetime.now()
            )
            
            self.strategy_states[strategy] = {
                "last_execution": None,
                "indicators": {},
                "positions": {}
            }
    
    def is_market_open(self, asset_type: str = "stocks") -> bool:
        """Check if market is open for given asset type"""
        now = datetime.now()
        
        if asset_type == "crypto":
            return True  # Crypto markets always open
            
        # For stocks/ETFs, check if it's a weekday and during market hours
        if now.weekday() >= 5:  # Weekend
            return False
            
        current_time = now.strftime("%H:%M")
        market_info = self.market_hours.get(asset_type, self.market_hours["stocks"])
        
        return market_info["open"] <= current_time <= market_info["close"]
    
    def generate_market_signals(self) -> List[TradingSignal]:
        """Generate trading signals using multiple strategies"""
        if not self.trading_config["signal_generation"]["enabled"]:
            logger.debug("Signal generation disabled in config")
            return []
            
        signals = []
        current_time = datetime.now()
        
        # Check if we should generate signals (rate limiting)
        last_signal = self.last_signal_time.get("global", current_time - timedelta(hours=1))
        time_since_last = (current_time - last_signal).total_seconds()
        required_interval = self.trading_config["signal_generation"]["interval_minutes"] * 60
        
        if time_since_last < required_interval:
            logger.debug(f"Rate limiting: {time_since_last:.1f}s < {required_interval}s required")
            return []
        
        # Get symbols for current mode
        current_mode = self.automation_engine.di_container.modes_config["current_mode"]
        available_symbols = self._get_symbols_for_mode(current_mode)
        logger.info(f"Generating signals for mode {current_mode} with {len(available_symbols)} symbols: {available_symbols}")
        
        # Generate signals from each enabled strategy
        enabled_strategies = self.trading_config["signal_generation"]["strategies_enabled"]
        logger.info(f"Using strategies: {enabled_strategies}")
        
        for strategy in enabled_strategies:
            try:
                strategy_signals = self._generate_strategy_signals(strategy, available_symbols)
                logger.info(f"Strategy {strategy} generated {len(strategy_signals)} signals")
                signals.extend(strategy_signals)
            except Exception as e:
                logger.error(f"Error generating signals for {strategy}: {e}")
        
        logger.info(f"Total raw signals before filtering: {len(signals)}")
        
        # Filter by signal strength and rate limits
        filtered_signals = self._filter_signals(signals)
        logger.info(f"Signals after filtering: {len(filtered_signals)}")
        
        if filtered_signals:
            self.last_signal_time["global"] = current_time
            logger.info(f"Generated {len(filtered_signals)} signals from {len(enabled_strategies)} strategies")
        else:
            logger.warning("No signals generated after all processing steps")
        
        return filtered_signals
    
    def _get_symbols_for_mode(self, mode: str) -> List[str]:
        """Get available symbols for current trading mode"""
        symbols = []
        
        if mode == "tradestation_only":
            symbols.extend(self.trading_config["symbols"]["stocks"])
            symbols.extend(self.trading_config["symbols"]["etfs"])
        elif mode == "hybrid":
            symbols.extend(self.trading_config["symbols"]["stocks"])
            symbols.extend(self.trading_config["symbols"]["etfs"])
            symbols.extend(self.trading_config["symbols"]["crypto"])
        elif mode == "defi_only":
            symbols.extend(self.trading_config["symbols"]["crypto"])
        
        return symbols
    
    def _generate_strategy_signals(self, strategy: str, symbols: List[str]) -> List[TradingSignal]:
        """Generate signals for specific strategy"""
        signals = []
        
        for symbol in symbols:
            try:
                # Get recent price data (simulated for now)
                price_data = self._get_price_data(symbol)
                
                if strategy == "ma_crossover":
                    signal = self._ma_crossover_strategy(symbol, price_data)
                elif strategy == "rsi_mean_reversion":
                    signal = self._rsi_mean_reversion_strategy(symbol, price_data)
                elif strategy == "momentum_breakout":
                    signal = self._momentum_breakout_strategy(symbol, price_data)
                else:
                    continue
                    
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating {strategy} signal for {symbol}: {e}")
        
        return signals
    
    def _get_price_data(self, symbol: str, periods: int = 50) -> Dict[str, Any]:
        """Get simulated price data for symbol"""
        # In production, this would use real price provider
        # For now, generate realistic price movements
        
        if symbol not in self.price_history:
            # Initialize with base price
            base_prices = {
                "AAPL": 175.0, "MSFT": 350.0, "GOOGL": 140.0, "AMZN": 145.0,
                "TSLA": 250.0, "NVDA": 450.0, "META": 300.0,
                "ETH": 2500.0, "BTC": 45000.0, "USDC": 1.0,
                "SPY": 450.0, "QQQ": 380.0, "IWM": 200.0, "VTI": 220.0
            }
            
            base_price = base_prices.get(symbol, 100.0)
            self.price_history[symbol] = []
            
            # Generate initial history
            for i in range(periods):
                price = base_price * (1 + random.gauss(0, 0.02))  # 2% daily volatility
                self.price_history[symbol].append({
                    "timestamp": datetime.now() - timedelta(days=periods-i),
                    "price": price,
                    "volume": random.randint(1000000, 10000000)
                })
        
        # Add new price point
        last_price = self.price_history[symbol][-1]["price"]
        volatility = 0.015 if symbol in ["AAPL", "MSFT", "GOOGL"] else 0.025
        if "BTC" in symbol or "ETH" in symbol:
            volatility = 0.04
            
        new_price = last_price * (1 + random.gauss(0, volatility))
        
        self.price_history[symbol].append({
            "timestamp": datetime.now(),
            "price": new_price,
            "volume": random.randint(1000000, 10000000)
        })
        
        # Keep only last N periods
        if len(self.price_history[symbol]) > periods:
            self.price_history[symbol] = self.price_history[symbol][-periods:]
        
        # Calculate indicators
        prices = [p["price"] for p in self.price_history[symbol]]
        
        return {
            "symbol": symbol,
            "current_price": new_price,
            "prices": prices,
            "sma_15": sum(prices[-15:]) / min(15, len(prices)) if prices else new_price,
            "sma_50": sum(prices[-50:]) / min(50, len(prices)) if prices else new_price,
            "rsi": self._calculate_rsi(prices),
            "volume": self.price_history[symbol][-1]["volume"]
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d for d in deltas if d > 0]
        losses = [abs(d) for d in deltas if d < 0]
        
        avg_gain = sum(gains[-period:]) / len(gains[-period:]) if gains[-period:] else 0
        avg_loss = sum(losses[-period:]) / len(losses[-period:]) if losses[-period:] else 0
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _ma_crossover_strategy(self, symbol: str, price_data: Dict) -> Optional[TradingSignal]:
        """Moving average crossover strategy"""
        sma_15 = price_data["sma_15"]
        sma_50 = price_data["sma_50"]
        current_price = price_data["current_price"]
        
        # Get previous MA values (simulated)
        prev_sma_15 = sma_15 * (1 + random.gauss(0, 0.001))
        prev_sma_50 = sma_50 * (1 + random.gauss(0, 0.001))
        
        signal_strength = SignalStrength.WEAK
        side = None
        
        # Bullish crossover: 15-day MA crosses above 50-day MA
        if sma_15 > sma_50 and prev_sma_15 <= prev_sma_50:
            side = OrderSide.BUY
            strength_factor = (sma_15 - sma_50) / sma_50
            if strength_factor > 0.02:
                signal_strength = SignalStrength.STRONG
            elif strength_factor > 0.01:
                signal_strength = SignalStrength.MODERATE
                
        # Bearish crossover: 15-day MA crosses below 50-day MA
        elif sma_15 < sma_50 and prev_sma_15 >= prev_sma_50:
            side = OrderSide.SELL
            strength_factor = abs(sma_15 - sma_50) / sma_50
            if strength_factor > 0.02:
                signal_strength = SignalStrength.STRONG
            elif strength_factor > 0.01:
                signal_strength = SignalStrength.MODERATE
        
        # Enhanced signal generation: also trigger on momentum conditions
        if not side and random.random() < 0.1:  # 10% chance to generate momentum signal
            if sma_15 > sma_50 * 1.005:  # Price momentum upward
                side = OrderSide.BUY
                signal_strength = SignalStrength.WEAK
            elif sma_15 < sma_50 * 0.995:  # Price momentum downward  
                side = OrderSide.SELL
                signal_strength = SignalStrength.WEAK
        
        if side and signal_strength.value in ["weak", "moderate", "strong", "very_strong"]:
            logger.info(f"MA crossover signal: {symbol} {side.value} strength={signal_strength.value}")
            return TradingSignal(
                id=str(uuid.uuid4()),
                symbol=symbol,
                side=side,
                quantity=self._calculate_position_size(symbol, current_price),
                order_type=OrderType.MARKET,
                price=current_price,
                metadata={
                    "strategy": "ma_crossover",
                    "signal_strength": signal_strength.value,
                    "sma_15": sma_15,
                    "sma_50": sma_50,
                    "reasoning": f"MA crossover: 15-day={sma_15:.2f}, 50-day={sma_50:.2f}"
                }
            )
        
        return None
    
    def _rsi_mean_reversion_strategy(self, symbol: str, price_data: Dict) -> Optional[TradingSignal]:
        """RSI mean reversion strategy"""
        rsi = price_data["rsi"]
        current_price = price_data["current_price"]
        
        signal_strength = SignalStrength.WEAK
        side = None
        
        # Oversold condition
        if rsi < 30:
            side = OrderSide.BUY
            if rsi < 20:
                signal_strength = SignalStrength.VERY_STRONG
            elif rsi < 25:
                signal_strength = SignalStrength.STRONG
            else:
                signal_strength = SignalStrength.MODERATE
                
        # Overbought condition
        elif rsi > 70:
            side = OrderSide.SELL
            if rsi > 80:
                signal_strength = SignalStrength.VERY_STRONG
            elif rsi > 75:
                signal_strength = SignalStrength.STRONG
            else:
                signal_strength = SignalStrength.MODERATE
        
        if side and signal_strength.value in ["moderate", "strong", "very_strong"]:
            return TradingSignal(
                id=str(uuid.uuid4()),
                symbol=symbol,
                side=side,
                quantity=self._calculate_position_size(symbol, current_price),
                order_type=OrderType.MARKET,
                price=current_price,
                metadata={
                    "strategy": "rsi_mean_reversion",
                    "signal_strength": signal_strength.value,
                    "rsi": rsi,
                    "reasoning": f"RSI {rsi:.1f} - {'oversold' if rsi < 30 else 'overbought'}"
                }
            )
        
        return None
    
    def _momentum_breakout_strategy(self, symbol: str, price_data: Dict) -> Optional[TradingSignal]:
        """Momentum breakout strategy"""
        prices = price_data["prices"]
        current_price = price_data["current_price"]
        
        if len(prices) < 20:
            return None
        
        # Calculate recent high/low
        recent_high = max(prices[-20:])
        recent_low = min(prices[-20:])
        
        signal_strength = SignalStrength.WEAK
        side = None
        
        # Breakout above recent high
        if current_price > recent_high * 1.01:  # 1% above recent high
            side = OrderSide.BUY
            breakout_strength = (current_price - recent_high) / recent_high
            if breakout_strength > 0.03:
                signal_strength = SignalStrength.STRONG
            elif breakout_strength > 0.015:
                signal_strength = SignalStrength.MODERATE
                
        # Breakdown below recent low
        elif current_price < recent_low * 0.99:  # 1% below recent low
            side = OrderSide.SELL
            breakdown_strength = (recent_low - current_price) / recent_low
            if breakdown_strength > 0.03:
                signal_strength = SignalStrength.STRONG
            elif breakdown_strength > 0.015:
                signal_strength = SignalStrength.MODERATE
        
        if side and signal_strength.value in ["moderate", "strong", "very_strong"]:
            return TradingSignal(
                id=str(uuid.uuid4()),
                symbol=symbol,
                side=side,
                quantity=self._calculate_position_size(symbol, current_price),
                order_type=OrderType.MARKET,
                price=current_price,
                metadata={
                    "strategy": "momentum_breakout",
                    "signal_strength": signal_strength.value,
                    "recent_high": recent_high,
                    "recent_low": recent_low,
                    "reasoning": f"Breakout: price {current_price:.2f} vs range {recent_low:.2f}-{recent_high:.2f}"
                }
            )
        
        return None
    
    def _calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate appropriate position size based on risk management"""
        try:
            # Get available capital using dynamic portfolio manager
            if self.automation_engine.capital_manager.is_initialized:
                available_capital = self.automation_engine.capital_manager.get_available_capital()
                max_position_size = self.automation_engine.capital_manager.get_max_position_size()
            else:
                # Use dynamic portfolio manager instead of hardcoded values
                try:
                    from core.dynamic_portfolio_manager import get_portfolio_manager
                    from core.config_manager import SystemConfig
                    
                    config = SystemConfig()
                    portfolio_manager = get_portfolio_manager(config)
                    available_capital = portfolio_manager.get_current_portfolio_value()
                    max_position_size = available_capital * 0.10  # 10% default
                    
                    logger.info(f"Using dynamic capital: ${available_capital:,.2f}")
                except Exception as e:
                    # Emergency fallback only
                    logger.warning(f"Failed to get dynamic capital, using fallback: {e}")
                    available_capital = 500.0    # Emergency fallback
                    max_position_size = 50.0     # 10% default
            
            # Use smaller of configured max and risk management limit
            risk_max_pct = self.trading_config["risk_management"]["max_position_size_pct"] / 100.0
            position_limit = min(max_position_size, available_capital * risk_max_pct)
            
            # Calculate quantity
            quantity = position_limit / price
            
            # Round to appropriate decimal places
            if symbol in ["BTC", "ETH"]:
                quantity = round(quantity, 4)
            elif symbol in ["USDC"]:
                quantity = round(quantity, 2)
            else:
                quantity = int(max(1, quantity))  # Whole shares for stocks
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 1.0  # Default minimal position
    
    def _filter_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Filter signals based on quality and rate limits"""
        if not signals:
            return []
        
        # Filter by signal strength
        min_strength = self.trading_config["signal_generation"]["min_signal_strength"]
        strength_order = {"weak": 0, "moderate": 1, "strong": 2, "very_strong": 3}
        min_level = strength_order.get(min_strength, 1)
        
        filtered = []
        for signal in signals:
            signal_strength = signal.metadata.get("signal_strength", "weak")
            if strength_order.get(signal_strength, 0) >= min_level:
                filtered.append(signal)
        
        # Limit by max signals per hour
        max_signals = self.trading_config["signal_generation"]["max_signals_per_hour"]
        if len(filtered) > max_signals:
            # Sort by strength and take the strongest signals
            filtered.sort(key=lambda s: strength_order.get(s.metadata.get("signal_strength", "weak"), 0), reverse=True)
            filtered = filtered[:max_signals]
        
        return filtered
    
    def execute_paper_trade(self, signal: TradingSignal) -> PaperTrade:
        """Execute a paper trade with realistic simulation"""
        try:
            # Simulate execution with slippage and fees
            symbol = signal.symbol
            asset_type = self._get_asset_type(symbol)
            
            # Calculate slippage
            slippage_pct = self.trading_config["execution"]["slippage"][asset_type] / 100.0
            slippage_factor = random.uniform(0.5, 1.5) * slippage_pct  # Variable slippage
            
            if signal.side == OrderSide.BUY:
                execution_price = signal.price * (1 + slippage_factor)
            else:
                execution_price = signal.price * (1 - slippage_factor)
            
            # Calculate fees
            current_mode = self.automation_engine.di_container.modes_config["current_mode"]
            if "defi" in current_mode and asset_type == "crypto":
                fees = self.trading_config["execution"]["fees"]["defi"]
            else:
                fees = self.trading_config["execution"]["fees"]["tradestation"]
            
            # Create paper trade
            paper_trade = PaperTrade(
                trade_id=str(uuid.uuid4()),
                signal_id=signal.id,
                symbol=symbol,
                side=signal.side.value,
                quantity=signal.quantity,
                entry_price=execution_price,
                entry_time=datetime.now(),
                fees=fees,
                slippage=abs(execution_price - signal.price),
                strategy=signal.metadata.get("strategy", "unknown"),
                mode=current_mode,
                status="open",
                metadata={
                    "original_price": signal.price,
                    "slippage_pct": slippage_factor * 100,
                    "signal_strength": signal.metadata.get("signal_strength", "unknown"),
                    "reasoning": signal.metadata.get("reasoning", "")
                }
            )
            
            # Store trade
            self.paper_trades[paper_trade.trade_id] = paper_trade
            if signal.side == OrderSide.BUY:
                self.open_positions[symbol] = paper_trade
            
            # Update statistics
            self.total_trades += 1
            strategy = paper_trade.strategy
            if strategy in self.strategy_performances:
                self.strategy_performances[strategy].executed_trades += 1
            
            logger.info(f"Paper trade executed: {symbol} {signal.side.value} {signal.quantity} @ {execution_price:.4f}")
            return paper_trade
            
        except Exception as e:
            logger.error(f"Error executing paper trade for {signal.symbol}: {e}")
            raise
    
    def _get_asset_type(self, symbol: str) -> str:
        """Determine asset type for symbol"""
        if symbol in self.trading_config["symbols"]["crypto"]:
            return "crypto"
        elif symbol in self.trading_config["symbols"]["etfs"]:
            return "etfs"
        else:
            return "stocks"
    
    def manage_positions(self):
        """Manage open positions with stop losses and take profits"""
        positions_to_close = []
        
        for symbol, position in self.open_positions.items():
            try:
                # Get current price
                current_data = self._get_price_data(symbol, 1)
                current_price = current_data["current_price"]
                
                # Calculate P&L
                if position.side == "buy":
                    pnl = (current_price - position.entry_price) * position.quantity - position.fees
                    pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
                else:
                    pnl = (position.entry_price - current_price) * position.quantity - position.fees
                    pnl_pct = (position.entry_price - current_price) / position.entry_price * 100
                
                # Update unrealized P&L for open position
                position.pnl = pnl
                
                # Check stop loss
                stop_loss_pct = self.trading_config["risk_management"]["stop_loss_pct"]
                if pnl_pct < -stop_loss_pct:
                    positions_to_close.append((symbol, current_price, "stop_loss", pnl))
                    continue
                
                # Check take profit
                take_profit_pct = self.trading_config["risk_management"]["take_profit_pct"]
                if pnl_pct > take_profit_pct:
                    positions_to_close.append((symbol, current_price, "take_profit", pnl))
                    continue
                
                # Check time-based exit (hold for max 24 hours)
                if datetime.now() - position.entry_time > timedelta(hours=24):
                    positions_to_close.append((symbol, current_price, "time_exit", pnl))
                
            except Exception as e:
                logger.error(f"Error managing position for {symbol}: {e}")
        
        # Close positions that meet exit criteria
        for symbol, exit_price, exit_reason, pnl in positions_to_close:
            self._close_position(symbol, exit_price, exit_reason, pnl)
    
    def update_unrealized_pnl(self):
        """Update unrealized P&L for all open positions"""
        try:
            for symbol, position in self.open_positions.items():
                # Get current price
                current_data = self._get_price_data(symbol, 1)
                current_price = current_data["current_price"]
                
                # Calculate unrealized P&L
                if position.side == "buy":
                    pnl = (current_price - position.entry_price) * position.quantity - position.fees
                else:
                    pnl = (position.entry_price - current_price) * position.quantity - position.fees
                
                # Update position P&L
                position.pnl = pnl
                
                # Also update in paper_trades dict if it exists
                if position.trade_id in self.paper_trades:
                    self.paper_trades[position.trade_id].pnl = pnl
                    
        except Exception as e:
            logger.error(f"Error updating unrealized P&L: {e}")
    
    def _close_position(self, symbol: str, exit_price: float, reason: str, pnl: float):
        """Close an open position"""
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            
            # Update position
            position.exit_price = exit_price
            position.exit_time = datetime.now()
            position.pnl = pnl
            position.status = f"closed_{reason}"
            
            # Update totals
            self.total_pnl += pnl
            self.daily_pnl += pnl
            
            # Update strategy performance
            strategy = position.strategy
            if strategy in self.strategy_performances:
                perf = self.strategy_performances[strategy]
                perf.total_pnl += pnl
                
                if pnl > 0:
                    perf.winning_trades += 1
                    perf.avg_win = (perf.avg_win * (perf.winning_trades - 1) + pnl) / perf.winning_trades
                else:
                    perf.losing_trades += 1
                    perf.avg_loss = (perf.avg_loss * (perf.losing_trades - 1) + abs(pnl)) / perf.losing_trades
                
                total_closed = perf.winning_trades + perf.losing_trades
                if total_closed > 0:
                    perf.win_rate = (perf.winning_trades / total_closed) * 100
                
                perf.last_updated = datetime.now()
            
            # Remove from open positions
            del self.open_positions[symbol]
            
            logger.info(f"Position closed: {symbol} {reason} P&L: ${pnl:.2f}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        runtime_hours = (datetime.now() - self.system_start_time).total_seconds() / 3600
        
        summary = {
            "overall_performance": {
                "total_pnl": self.total_pnl,
                "daily_pnl": self.daily_pnl,
                "total_trades": self.total_trades,
                "open_positions": len(self.open_positions),
                "runtime_hours": round(runtime_hours, 2),
                "avg_trades_per_hour": round(self.total_trades / max(runtime_hours, 0.1), 2)
            },
            "strategy_performance": {},
            "current_positions": [],
            "recent_trades": [],
            "system_status": {
                "is_running": self.is_running,
                "current_mode": self.automation_engine.di_container.modes_config["current_mode"],
                "market_open": self.is_market_open("stocks"),
                "last_signal_time": self.last_signal_time.get("global", "never")
            }
        }
        
        # Strategy performance details
        for strategy, perf in self.strategy_performances.items():
            summary["strategy_performance"][strategy] = asdict(perf)
        
        # Current positions
        for symbol, position in self.open_positions.items():
            current_data = self._get_price_data(symbol, 1)
            current_price = current_data["current_price"]
            
            if position.side == "buy":
                current_pnl = (current_price - position.entry_price) * position.quantity - position.fees
            else:
                current_pnl = (position.entry_price - current_price) * position.quantity - position.fees
            
            summary["current_positions"].append({
                "symbol": symbol,
                "side": position.side,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "pnl": round(current_pnl, 2),
                "entry_time": position.entry_time.isoformat(),
                "strategy": position.strategy
            })
        
        # Recent trades
        recent_trades = sorted(
            [t for t in self.paper_trades.values() if t.status.startswith("closed")],
            key=lambda x: x.exit_time or x.entry_time,
            reverse=True
        )[:10]
        
        for trade in recent_trades:
            summary["recent_trades"].append({
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "strategy": trade.strategy,
                "exit_reason": trade.status.split("_", 1)[1] if "_" in trade.status else trade.status
            })
        
        return summary
    
    async def run_continuous_trading(self):
        """Main trading loop - runs continuously"""
        logger.info("Starting continuous paper trading engine")
        self.is_running = True
        
        while self.is_running:
            try:
                # Generate and process signals
                signals = self.generate_market_signals()
                
                for signal in signals:
                    try:
                        # Process signal through automation engine
                        processed_signal = self.automation_engine.process_signal(signal)
                        
                        # If executed, create paper trade record
                        if processed_signal.status == SignalStatus.EXECUTED:
                            paper_trade = self.execute_paper_trade(signal)
                            logger.info(f"New paper trade: {paper_trade.symbol} {paper_trade.side}")
                        
                    except Exception as e:
                        logger.error(f"Error processing signal {signal.symbol}: {e}")
                
                # Manage existing positions
                self.manage_positions()
                
                # Log periodic status
                if self.total_trades > 0 and self.total_trades % 10 == 0:
                    logger.info(f"Trading status: {self.total_trades} trades, P&L: ${self.total_pnl:.2f}")
                
                # Wait before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def start_trading(self):
        """Start the paper trading engine"""
        if not self.is_running:
            # Run in separate thread to not block main application
            def run_trading():
                asyncio.run(self.run_continuous_trading())
            
            trading_thread = threading.Thread(target=run_trading, daemon=True)
            trading_thread.start()
            
            logger.info("Paper trading engine started")
            return True
        return False
    
    def stop_trading(self):
        """Stop the paper trading engine"""
        self.is_running = False
        logger.info("Paper trading engine stopped")
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get comprehensive trading status"""
        open_positions = {k: v for k, v in self.paper_trades.items() if v.exit_time is None}
        
        return {
            "is_running": self.is_running,
            "total_trades": len(self.paper_trades),
            "open_positions": len(open_positions),
            "total_pnl": sum(trade.pnl or 0 for trade in self.paper_trades.values()),
            "realized_pnl": sum(trade.pnl or 0 for trade in self.paper_trades.values() if trade.exit_time and trade.pnl),
            "pnl": sum(trade.pnl or 0 for trade in open_positions.values()),
            "win_rate": self._calculate_win_rate(),
            "last_signal_time": max((trade.entry_time for trade in self.paper_trades.values()), default=None),
            "strategies_active": ["ma_crossover", "rsi_mean_reversion", "momentum_breakout"],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trading history"""
        sorted_trades = sorted(
            self.paper_trades.values(), 
            key=lambda x: x.entry_time, 
            reverse=True
        )
        
        return [asdict(trade) for trade in sorted_trades[:limit]]
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        open_positions = [
            trade for trade in self.paper_trades.values() 
            if trade.exit_time is None
        ]
        return [asdict(trade) for trade in open_positions]
    
    def close_position(self, trade_id: str) -> Dict[str, Any]:
        """Manually close a specific position"""
        if trade_id not in self.paper_trades:
            return {"error": f"Trade {trade_id} not found"}
        
        trade = self.paper_trades[trade_id]
        if trade.exit_time is not None:
            return {"error": f"Trade {trade_id} already closed"}
        
        # Get current market price for closure
        current_price = self._get_market_price(trade.symbol)
        
        # Close the trade
        trade.exit_time = datetime.now()
        trade.exit_price = current_price
        calculated_pnl = self._calculate_realized_pnl(trade)
        trade.pnl = calculated_pnl
        
        logger.info(f"Manually closed position {trade_id}: {trade.symbol} PnL: {calculated_pnl:.2f}")
        
        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": trade.symbol,
            "exit_price": current_price,
            "pnl": calculated_pnl,
            "timestamp": trade.exit_time.isoformat()
        }
    
    def clear_history(self) -> Dict[str, Any]:
        """Clear trading history (for testing)"""
        trades_cleared = len(self.paper_trades)
        self.paper_trades.clear()
        logger.info(f"Cleared {trades_cleared} paper trades")
        
        return {
            "success": True,
            "trades_cleared": trades_cleared,
            "timestamp": datetime.now().isoformat()
        }
    
    def start_continuous_trading(self, strategy: str = "mixed", signal_interval: int = 30) -> Dict[str, Any]:
        """Start continuous paper trading"""
        if self.is_running:
            return {"error": "Trading already running"}
        
        self.is_running = True
        
        # Start trading in a separate thread using proper signal processing pipeline
        def trading_loop():
            while self.is_running:
                try:
                    # Generate signals through the strategies
                    signals = self.generate_market_signals()
                    logger.info(f"Trading loop generated {len(signals)} signals")
                    
                    # Process each signal through the main automation engine
                    for signal in signals:
                        try:
                            logger.info(f"Processing signal: {signal.symbol} {signal.side.value} via automation engine")
                            # This is the key integration: use the main signal processing pipeline
                            processed_signal = self.automation_engine.process_signal(signal)
                            logger.info(f"Signal processed with status: {processed_signal.status}")
                            
                            # Create paper trade record if executed
                            if processed_signal.status == SignalStatus.EXECUTED:
                                paper_trade = self.execute_paper_trade(signal)
                                logger.info(f"Paper trade created: {paper_trade.symbol} {paper_trade.side} - Trade ID: {paper_trade.trade_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing signal {signal.symbol}: {e}")
                    
                    time.sleep(signal_interval * 60)  # Convert minutes to seconds
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        threading.Thread(target=trading_loop, daemon=True).start()
        logger.info(f"Started continuous trading with {strategy} strategy, {signal_interval}min intervals")
        
        return {
            "success": True,
            "strategy": strategy,
            "signal_interval": signal_interval,
            "timestamp": datetime.now().isoformat()
        }
    
    def stop_continuous_trading(self) -> Dict[str, Any]:
        """Stop continuous trading"""
        self.is_running = False
        logger.info("Stopped continuous trading")
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from closed trades"""
        closed_trades = [trade for trade in self.paper_trades.values() if trade.exit_time is not None]
        if not closed_trades:
            return 0.0
        
        winning_trades = [trade for trade in closed_trades if trade.pnl and trade.pnl > 0]
        return (len(winning_trades) / len(closed_trades)) * 100
    
    def generate_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive performance analysis"""
        from_date = datetime.now() - timedelta(days=days)
        
        # Filter trades within the specified period
        period_trades = [
            trade for trade in self.paper_trades.values()
            if trade.entry_time >= from_date
        ]
        
        closed_trades = [trade for trade in period_trades if trade.exit_time is not None]
        open_trades = [trade for trade in period_trades if trade.exit_time is None]
        
        # Calculate basic metrics
        total_realized_pnl = sum(trade.pnl or 0 for trade in closed_trades)
        total_unrealized_pnl = sum(trade.pnl or 0 for trade in open_trades)
        total_pnl = total_realized_pnl + total_unrealized_pnl
        
        # Win/Loss analysis
        winning_trades = [trade for trade in closed_trades if trade.pnl and trade.pnl > 0]
        losing_trades = [trade for trade in closed_trades if trade.pnl and trade.pnl < 0]
        
        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        # Average trade metrics
        avg_win = sum(trade.pnl for trade in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(trade.pnl for trade in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Strategy breakdown
        strategy_performance = {}
        for trade in period_trades:
            strategy = trade.metadata.get('strategy', 'unknown') if trade.metadata else 'unknown'
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    'trades': 0,
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            strategy_performance[strategy]['trades'] += 1
            if trade.pnl:
                strategy_performance[strategy]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    strategy_performance[strategy]['wins'] += 1
                else:
                    strategy_performance[strategy]['losses'] += 1
        
        # Calculate win rates for each strategy
        for strategy, stats in strategy_performance.items():
            total_completed = stats['wins'] + stats['losses']
            stats['win_rate'] = (stats['wins'] / total_completed * 100) if total_completed > 0 else 0
        
        # Risk metrics
        returns = [trade.pnl for trade in closed_trades if trade.pnl]
        
        if returns:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) if variance > 0 else 0
            sharpe_ratio = (avg_return / volatility) if volatility > 0 else 0
        else:
            avg_return = volatility = sharpe_ratio = 0
        
        # Generate daily P&L series
        daily_pnl = {}
        for trade in period_trades:
            trade_date = trade.entry_time.date()
            if trade_date not in daily_pnl:
                daily_pnl[trade_date] = 0
            if trade.pnl:
                daily_pnl[trade_date] += trade.pnl
        
        # Sort daily P&L by date
        sorted_daily_pnl = [
            {"date": date.isoformat(), "pnl": pnl}
            for date, pnl in sorted(daily_pnl.items())
        ]
        
        return {
            "report_period": {
                "days": days,
                "from_date": from_date.isoformat(),
                "to_date": datetime.now().isoformat()
            },
            "summary": {
                "total_trades": len(period_trades),
                "closed_trades": len(closed_trades),
                "open_trades": len(open_trades),
                "total_pnl": round(total_pnl, 2),
                "realized_pnl": round(total_realized_pnl, 2),
                "current_pnl": round(total_unrealized_pnl, 2)
            },
            "performance_metrics": {
                "win_rate": round(win_rate, 1),
                "total_wins": len(winning_trades),
                "total_losses": len(losing_trades),
                "average_win": round(avg_win, 2),
                "average_loss": round(avg_loss, 2),
                "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else float('inf')
            },
            "risk_metrics": {
                "sharpe_ratio": round(sharpe_ratio, 3),
                "volatility": round(volatility, 2),
                "average_return": round(avg_return, 2),
                "max_drawdown": 0  # Simplified for now
            },
            "strategy_breakdown": strategy_performance,
            "daily_pnl": sorted_daily_pnl,
            "recent_trades": [
                {
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                    "pnl": trade.pnl
                }
                for trade in sorted(period_trades, key=lambda x: x.entry_time, reverse=True)[:10]
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_and_execute_signal(self, strategy: str = "mixed", symbol: Optional[str] = None) -> Dict[str, Any]:
        """Generate and execute a paper trading signal"""
        try:
            logger.info(f"Attempting to generate signal with strategy: {strategy}, symbol: {symbol}")
            
            # Generate signals based on strategy
            if strategy == "mixed":
                logger.info("Using mixed strategy - calling generate_market_signals()")
                signals = self.generate_market_signals()
            else:
                # Use existing strategy generation method
                symbols = [symbol] if symbol else ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
                logger.info(f"Using specific strategy {strategy} with symbols: {symbols}")
                signals = self._generate_strategy_signals(strategy, symbols)
            
            logger.info(f"Generated {len(signals)} signals")
            
            if not signals:
                logger.warning(f"No signals generated for strategy: {strategy}")
                return {
                    "success": False,
                    "message": f"No signals generated for strategy: {strategy}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Execute the first signal
            signal = signals[0]
            logger.info(f"Executing first signal: {signal.symbol} {signal.side.value}")
            trade_result = self.execute_paper_trade(signal)
            
            return {
                "success": True,
                "signal": {
                    "id": signal.id,
                    "symbol": signal.symbol,
                    "side": signal.side.value,
                    "quantity": signal.quantity,
                    "price": signal.price,
                    "strategy": strategy
                },
                "trade_result": asdict(trade_result) if trade_result else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating and executing signal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status for debugging"""
        return {
            **self.get_trading_status(),
            'signal_generation_config': self.config,
            'execution_mode': 'SIMULATION',
            'market_hours_bypassed': True,
            'risk_management_active': True
        }
    
    def force_execute_debug_trade(self, symbol: str, side: OrderSide, quantity: int, price: float) -> Dict[str, Any]:
        """Force execute a debug trade bypassing all restrictions"""
        try:
            import uuid
            from datetime import datetime
            
            # Create a paper trade directly
            trade_id = f"DEBUG_{uuid.uuid4().hex[:8]}"
            
            trade = PaperTrade(
                trade_id=trade_id,
                signal_id=f"DEBUG_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                entry_price=price,
                entry_time=datetime.now(),
                strategy='debug_forced',
                pnl=0.0  # Will be calculated later
            )
            
            self.paper_trades[trade_id] = trade
            logger.info(f"DEBUG TRADE FORCED: {symbol} {side.value} {quantity}@${price} - ID: {trade_id}")
            
            return {
                'trade_id': trade_id,
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity,
                'price': price,
                'status': 'executed'
            }
            
        except Exception as e:
            logger.error(f"Error forcing debug trade: {e}")
            raise