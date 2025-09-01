import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict

from .models import TradingSignal, SignalStatus, AccountStatus, RiskCheck
from .risk_manager import RiskManager
from .signal_processor import SignalProcessor
from .execution_router import ExecutionRouter
from config import trading_config, BLOCK_REASONS

logger = logging.getLogger(__name__)

class AutomationEngine:
    """Core automation engine that processes signals with zero manual intervention"""
    
    def __init__(self):
        self.risk_manager = RiskManager()
        self.signal_processor = SignalProcessor()
        self.execution_router = ExecutionRouter()
        self.active_signals: List[TradingSignal] = []
        
    def process_signal(self, signal: TradingSignal) -> TradingSignal:
        """
        Process a trading signal through the complete automation pipeline.
        Returns signal with final status: EXECUTED or BLOCKED(reason_code)
        """
        logger.info(f"Processing signal {signal.id}: {signal.symbol} {signal.side.value} {signal.quantity}")
        
        try:
            # Update signal status
            signal.status = SignalStatus.PROCESSING
            self.active_signals.append(signal)
            
            # Step 1: Risk management check
            risk_check = self.risk_manager.validate_trade(signal)
            if not risk_check.passed:
                return self._block_signal(signal, risk_check.reason)
            
            # Step 2: Signal processing and validation
            processed_signal = self.signal_processor.process(signal)
            if processed_signal.status == SignalStatus.BLOCKED:
                return processed_signal
            
            # Step 3: Route to execution venue
            executed_signal = self.execution_router.execute(processed_signal)
            
            # Step 4: Final status update
            if executed_signal.status == SignalStatus.EXECUTED:
                logger.info(f"Signal {signal.id} EXECUTED at {executed_signal.execution_price}")
            else:
                logger.warning(f"Signal {signal.id} BLOCKED: {executed_signal.block_reason}")
                
            return executed_signal
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.id}: {str(e)}")
            return self._block_signal(signal, BLOCK_REASONS['API_ERROR'])
    
    def _block_signal(self, signal: TradingSignal, reason: str) -> TradingSignal:
        """Block a signal with specified reason"""
        signal.status = SignalStatus.BLOCKED
        signal.block_reason = reason
        logger.warning(f"Signal {signal.id} blocked: {reason}")
        return signal
    
    def get_active_signals(self) -> List[TradingSignal]:
        """Get all active signals"""
        return [s for s in self.active_signals if s.status in [SignalStatus.RECEIVED, SignalStatus.PROCESSING]]
    
    def get_executed_signals(self) -> List[TradingSignal]:
        """Get all executed signals"""
        return [s for s in self.active_signals if s.status == SignalStatus.EXECUTED]
    
    def get_blocked_signals(self) -> List[TradingSignal]:
        """Get all blocked signals"""
        return [s for s in self.active_signals if s.status == SignalStatus.BLOCKED]
    
    def get_status_summary(self) -> dict:
        """Get summary of system status"""
        return {
            'total_signals': len(self.active_signals),
            'executed': len(self.get_executed_signals()),
            'blocked': len(self.get_blocked_signals()),
            'processing': len(self.get_active_signals()),
            'operating_mode': trading_config.operating_mode,
            'available_capital': trading_config.capital,
            'timestamp': datetime.now().isoformat()
        }