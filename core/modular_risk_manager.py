import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .models import TradingSignal, RiskCheck
from providers.base_providers import ExecutionProvider
from .capital_manager import CapitalManager

logger = logging.getLogger(__name__)

class ModularRiskManager:
    """Risk management system using injected execution provider"""
    
    def __init__(self, mode_config: Dict[str, Any], execution_provider: ExecutionProvider, capital_manager: Optional[CapitalManager] = None):
        self.mode_config = mode_config
        self.execution_provider = execution_provider
        
        # Initialize capital manager
        self.capital_manager = capital_manager or CapitalManager()
        
        # Extract risk limits from mode configuration (fallback values)
        risk_limits = mode_config.get("risk_limits", {})
        self.fallback_max_position_pct = risk_limits.get("max_position_pct", 0.10)
        self.fallback_max_daily_loss_pct = risk_limits.get("max_daily_loss_pct", 0.05)
        self.fallback_min_balance_threshold = risk_limits.get("min_balance_threshold", 14000)
        
        # Internal state
        self.daily_pnl = 0.0
        self.current_positions = {}
        self.last_reset = datetime.now().date()
        
        # Get effective limits (from capital manager or fallback)
        effective_limits = self._get_effective_risk_limits()
        logger.info(f"Risk manager initialized with limits: position={effective_limits['max_position_pct']:.1%}, daily_loss={effective_limits['max_daily_loss_pct']:.1%}")
    
    def _get_effective_risk_limits(self) -> Dict[str, float]:
        """Get effective risk limits from capital manager or fallback to config"""
        if self.capital_manager.is_initialized:
            allocation = self.capital_manager.get_allocation_summary()
            return {
                'max_position_pct': self.capital_manager.capital_config['allocation_percentages']['max_position_pct'] / 100.0,
                'max_daily_loss_pct': self.capital_manager.capital_config['allocation_percentages']['max_daily_loss_pct'] / 100.0
            }
        else:
            return {
                'max_position_pct': self.fallback_max_position_pct,
                'max_daily_loss_pct': self.fallback_max_daily_loss_pct
            }
        
    def validate_trade(self, signal: TradingSignal) -> RiskCheck:
        """
        Perform comprehensive risk validation using live account data
        """
        # Reset daily metrics if new day
        self._reset_daily_metrics()
        
        try:
            # Get capital and balance information
            if self.capital_manager.is_initialized:
                # Use capital manager for dynamic allocation
                is_valid, validation_message, details = self.capital_manager.validate_trade(
                    signal.symbol, signal.quantity, signal.price or 100
                )
                if not is_valid:
                    return RiskCheck(passed=False, reason=validation_message)
                
                available_balance = self.capital_manager.get_available_capital()
                max_position_value = self.capital_manager.get_max_position_size()
                max_daily_loss = self.capital_manager.get_max_daily_loss()
                min_threshold = self.capital_manager.get_total_capital() * 0.2
            else:
                # Fallback to execution provider balance
                available_balance = self.execution_provider.get_account_balance()
                if available_balance is None:
                    logger.warning("Could not retrieve account balance, using fallback default")
                    available_balance = self.fallback_min_balance_threshold + 2000
                
                max_position_value = available_balance * self.fallback_max_position_pct
                max_daily_loss = available_balance * self.fallback_max_daily_loss_pct
                min_threshold = self.fallback_min_balance_threshold
            
            # Calculate position value
            position_value = signal.quantity * (signal.price or 100)
            
            # Capital adequacy check already done by capital manager if initialized
            if not self.capital_manager.is_initialized and position_value > max_position_value:
                return RiskCheck(
                    passed=False, 
                    reason=f"Position size ${position_value:.2f} exceeds max allowed ${max_position_value:.2f}"
                )
            
            # Check 2: Daily loss limit
            if abs(self.daily_pnl) >= max_daily_loss:
                return RiskCheck(
                    passed=False,
                    reason=f"Daily loss ${abs(self.daily_pnl):.2f} exceeds limit ${max_daily_loss:.2f}"
                )
            
            # Check 3: Minimum account balance after trade
            projected_balance = available_balance - position_value
            if projected_balance < min_threshold:
                return RiskCheck(
                    passed=False,
                    reason=f"Projected balance ${projected_balance:.2f} below minimum ${min_threshold:.2f}"
                )
            
            # Check 4: Position concentration by symbol
            current_exposure = self._get_symbol_exposure(signal.symbol)
            total_exposure = current_exposure + position_value
            max_symbol_exposure = available_balance * 0.15  # 15% max per symbol
            
            if total_exposure > max_symbol_exposure:
                # Calculate maximum allowed quantity for this symbol
                remaining_capacity = max_symbol_exposure - current_exposure
                max_quantity = remaining_capacity / (signal.price or 100)
                
                if max_quantity <= 0:
                    return RiskCheck(
                        passed=False,
                        reason=f"Symbol {signal.symbol} exposure ${total_exposure:.2f} exceeds max ${max_symbol_exposure:.2f}"
                    )
                else:
                    return RiskCheck(
                        passed=True,
                        max_allowed_quantity=max_quantity
                    )
            
            # Check 5: Mode-specific symbol routing
            symbol_routing = self.mode_config.get("symbol_routing", {})
            symbol_type = self._classify_symbol(signal.symbol)
            allowed_venue = symbol_routing.get(symbol_type)
            
            if allowed_venue == "blocked":
                return RiskCheck(
                    passed=False,
                    reason=f"Symbol type '{symbol_type}' blocked in current mode"
                )
            
            # All checks passed
            logger.info(f"Risk check passed for {signal.symbol}: ${position_value:.2f} position (balance: ${available_balance:.2f})")
            return RiskCheck(passed=True)
            
        except Exception as e:
            logger.error(f"Error in risk validation: {e}")
            return RiskCheck(
                passed=False,
                reason=f"Risk validation error: {str(e)}"
            )
    
    def _classify_symbol(self, symbol: str) -> str:
        """Classify symbol type for routing rules"""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        crypto_patterns = ['BTC', 'ETH', 'USDT', 'USDC', 'DOGE', 'ADA', 'DOT', 'LINK']
        if any(crypto in symbol_upper for crypto in crypto_patterns):
            return "crypto"
        
        # ETF patterns (common ETF suffixes/patterns)
        if any(etf in symbol_upper for etf in ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'VTI', 'VOO']):
            return "etfs"
        
        # Options patterns (if they have option-like naming)
        if len(symbol) > 6 or any(char in symbol for char in ['C', 'P']) and symbol[-8:].isdigit():
            return "options"
        
        # Default to stocks
        return "stocks"
    
    def _reset_daily_metrics(self):
        """Reset daily metrics if new trading day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset:
            self.daily_pnl = 0.0
            self.last_reset = current_date
            logger.info("Daily risk metrics reset for new trading day")
    
    def _get_symbol_exposure(self, symbol: str) -> float:
        """Get current exposure for a symbol from live positions"""
        try:
            # Get live positions from execution provider
            positions = self.execution_provider.get_positions()
            
            total_exposure = 0.0
            for position in positions:
                if position.get('symbol', '').upper() == symbol.upper():
                    total_exposure += abs(position.get('market_value', 0.0))
            
            return total_exposure
            
        except Exception as e:
            logger.warning(f"Error getting live positions, using cached data: {e}")
            return self.current_positions.get(symbol.upper(), 0.0)
    
    def update_after_execution(self, signal: TradingSignal):
        """Update risk state after successful execution"""
        if signal.execution_price and signal.quantity:
            position_value = signal.quantity * signal.execution_price
            
            # Update position tracking
            symbol_upper = signal.symbol.upper()
            if signal.side.value == 'buy':
                self.current_positions[symbol_upper] = self.current_positions.get(symbol_upper, 0) + position_value
            else:  # sell
                self.current_positions[symbol_upper] = self.current_positions.get(symbol_upper, 0) - position_value
            
            # Clean up zero/minimal positions
            if abs(self.current_positions.get(symbol_upper, 0)) < 1.0:
                self.current_positions.pop(symbol_upper, None)
            
            logger.info(f"Updated position for {symbol_upper}: ${self.current_positions.get(symbol_upper, 0):.2f}")
    
    def update_daily_pnl(self, pnl_change: float):
        """Update daily PnL tracking"""
        self.daily_pnl += pnl_change
        logger.info(f"Daily PnL updated: ${self.daily_pnl:.2f}")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics with live data"""
        try:
            live_balance = self.execution_provider.get_account_balance()
            live_positions = self.execution_provider.get_positions()
            
            return {
                'daily_pnl': self.daily_pnl,
                'daily_loss_limit': (live_balance or self.min_balance_threshold) * self.max_daily_loss_pct,
                'available_balance': live_balance,
                'min_balance_threshold': self.min_balance_threshold,
                'max_position_size': (live_balance or self.min_balance_threshold) * self.max_position_pct,
                'max_position_pct': self.max_position_pct,
                'max_daily_loss_pct': self.max_daily_loss_pct,
                'current_positions_count': len(live_positions) if live_positions else len(self.current_positions),
                'cached_positions': dict(self.current_positions),
                'live_positions': live_positions[:5] if live_positions else [],  # Limit for display
                'last_reset': self.last_reset.isoformat(),
                'mode': self.mode_config.get('description', 'Unknown'),
                'symbol_routing': self.mode_config.get('symbol_routing', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return {
                'error': str(e),
                'daily_pnl': self.daily_pnl,
                'last_reset': self.last_reset.isoformat()
            }