import logging
from datetime import datetime, timedelta
from typing import Optional

from .models import TradingSignal, RiskCheck, AccountStatus
from config import trading_config, BLOCK_REASONS

logger = logging.getLogger(__name__)

class RiskManager:
    """Risk management system with automated validation"""
    
    def __init__(self):
        self.daily_pnl = 0.0
        self.current_positions = {}
        self.last_reset = datetime.now().date()
        
    def validate_trade(self, signal: TradingSignal) -> RiskCheck:
        """
        Perform comprehensive risk validation on a trading signal
        Returns RiskCheck with pass/fail status and reason
        """
        # Reset daily PnL if new day
        self._reset_daily_metrics()
        
        # Check 1: Capital adequacy
        position_value = signal.quantity * (signal.price or 100)  # Use signal price or estimate
        if position_value > trading_config.capital * trading_config.max_position_size_pct:
            return RiskCheck(
                passed=False, 
                reason=BLOCK_REASONS['MAX_POSITION_EXCEEDED']
            )
        
        # Check 2: Daily loss limit
        max_daily_loss = trading_config.capital * trading_config.max_daily_loss_pct
        if abs(self.daily_pnl) >= max_daily_loss:
            return RiskCheck(
                passed=False,
                reason=BLOCK_REASONS['DAILY_LOSS_LIMIT']
            )
        
        # Check 3: Minimum account balance
        projected_balance = trading_config.capital - position_value
        if projected_balance < trading_config.min_account_balance:
            return RiskCheck(
                passed=False,
                reason=BLOCK_REASONS['INSUFFICIENT_CAPITAL']
            )
        
        # Check 4: Position concentration
        current_exposure = self._get_symbol_exposure(signal.symbol)
        total_exposure = current_exposure + position_value
        max_symbol_exposure = trading_config.capital * 0.15  # 15% max per symbol
        
        if total_exposure > max_symbol_exposure:
            # Calculate maximum allowed quantity
            remaining_capacity = max_symbol_exposure - current_exposure
            max_quantity = remaining_capacity / (signal.price or 100)
            
            if max_quantity <= 0:
                return RiskCheck(
                    passed=False,
                    reason=BLOCK_REASONS['MAX_POSITION_EXCEEDED']
                )
            else:
                return RiskCheck(
                    passed=True,
                    max_allowed_quantity=max_quantity
                )
        
        # All checks passed
        logger.info(f"Risk check passed for {signal.symbol}: ${position_value:.2f} position")
        return RiskCheck(passed=True)
    
    def _reset_daily_metrics(self):
        """Reset daily metrics if new trading day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset:
            self.daily_pnl = 0.0
            self.last_reset = current_date
            logger.info("Daily metrics reset for new trading day")
    
    def _get_symbol_exposure(self, symbol: str) -> float:
        """Get current exposure for a symbol"""
        return self.current_positions.get(symbol, 0.0)
    
    def update_position(self, symbol: str, quantity: float, price: float):
        """Update position tracking"""
        position_value = quantity * price
        self.current_positions[symbol] = self.current_positions.get(symbol, 0) + position_value
        
        # Clean up zero positions
        if abs(self.current_positions[symbol]) < 0.01:
            del self.current_positions[symbol]
    
    def update_daily_pnl(self, pnl_change: float):
        """Update daily PnL tracking"""
        self.daily_pnl += pnl_change
        logger.info(f"Daily PnL updated: ${self.daily_pnl:.2f}")
    
    def get_risk_metrics(self) -> dict:
        """Get current risk metrics"""
        return {
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': trading_config.capital * trading_config.max_daily_loss_pct,
            'available_capital': trading_config.capital,
            'min_balance_threshold': trading_config.min_account_balance,
            'max_position_size': trading_config.capital * trading_config.max_position_size_pct,
            'current_positions': dict(self.current_positions),
            'last_reset': self.last_reset.isoformat()
        }