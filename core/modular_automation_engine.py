import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .models import TradingSignal, SignalStatus
from .modular_risk_manager import ModularRiskManager
from .modular_signal_processor import ModularSignalProcessor
from .modular_execution_router import ModularExecutionRouter
from .di_container import DIContainer
from .capital_manager import CapitalManager
from .execution_mode_manager import ExecutionModeManager
from providers.base_providers import PriceDataProvider, ExecutionProvider, NewsProvider, AnalyticsProvider

logger = logging.getLogger(__name__)

class ModularAutomationEngine:
    """Modular automation engine using dependency injection"""
    
    def __init__(self, di_container: DIContainer, capital_manager: Optional[CapitalManager] = None, execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.di_container = di_container
        self.capital_manager = capital_manager or CapitalManager()
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        self.active_signals: List[TradingSignal] = []
        
        # Initialize components with injected dependencies
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize core components with injected providers"""
        try:
            # Get providers from DI container
            price_provider = self.di_container.get_price_provider()
            execution_provider = self.di_container.get_execution_provider()
            news_provider = self.di_container.get_news_provider()  # Optional
            analytics_provider = self.di_container.get_analytics_provider()  # Optional
            
            # Initialize risk manager with mode configuration and capital manager
            mode_config = self.di_container.get_current_mode_config()
            self.risk_manager = ModularRiskManager(
                mode_config=mode_config,
                execution_provider=execution_provider,
                capital_manager=self.capital_manager
            )
            
            # Initialize signal processor with providers
            self.signal_processor = ModularSignalProcessor(
                price_provider=price_provider,
                news_provider=news_provider,
                analytics_provider=analytics_provider,
                mode_config=mode_config,
                execution_mode_manager=self.execution_mode_manager
            )
            
            # Initialize execution router with providers
            self.execution_router = ModularExecutionRouter(
                execution_provider=execution_provider,
                mode_config=mode_config,
                execution_mode_manager=self.execution_mode_manager
            )
            
            logger.info("Modular automation engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing modular automation engine: {e}")
            raise
    
    def process_signal(self, signal: TradingSignal) -> TradingSignal:
        """
        Process a trading signal through the complete automation pipeline
        Returns signal with final status: EXECUTED or BLOCKED(reason_code)
        """
        logger.info(f"Processing signal {signal.id}: {signal.symbol} {signal.side.value} {signal.quantity}")
        
        try:
            # Update signal status
            signal.status = SignalStatus.PROCESSING
            self.active_signals.append(signal)
            
            # Step 1: Risk management check
            risk_result = self.risk_manager.validate_trade(signal)
            if not risk_result.passed:
                return self._block_signal(signal, risk_result.reason)
            
            # Apply risk management adjustments if needed
            if risk_result.max_allowed_quantity and risk_result.max_allowed_quantity < signal.quantity:
                logger.info(f"Reducing quantity from {signal.quantity} to {risk_result.max_allowed_quantity}")
                signal.quantity = risk_result.max_allowed_quantity
            
            # Step 2: Signal processing and validation
            processed_signal = self.signal_processor.process(signal)
            if processed_signal.status == SignalStatus.BLOCKED:
                return processed_signal
            
            # Step 3: Route to execution
            executed_signal = self.execution_router.execute(processed_signal)
            
            # Step 4: Update risk manager with execution results
            if executed_signal.status == SignalStatus.EXECUTED:
                self.risk_manager.update_after_execution(executed_signal)
                logger.info(f"Signal {signal.id} EXECUTED at {executed_signal.execution_price}")
            else:
                logger.warning(f"Signal {signal.id} BLOCKED: {executed_signal.block_reason}")
                
            return executed_signal
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.id}: {str(e)}")
            return self._block_signal(signal, f"System error: {str(e)}")
    
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
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        mode_config = self.di_container.get_current_mode_config()
        provider_health = self.di_container.health_check_all_providers()
        
        return {
            'total_signals': len(self.active_signals),
            'executed': len(self.get_executed_signals()),
            'blocked': len(self.get_blocked_signals()),
            'processing': len(self.get_active_signals()),
            'operating_mode': self.di_container.modes_config["current_mode"],
            'available_capital': mode_config.get("risk_limits", {}).get("min_balance_threshold", 16000),
            'timestamp': datetime.now().isoformat(),
            'providers': {
                'price_data': self._serialize_provider_health(provider_health.get('price_data')),
                'execution': self._serialize_provider_health(provider_health.get('execution')),
                'news': self._serialize_provider_health(provider_health.get('news')),
                'analytics': self._serialize_provider_health(provider_health.get('analytics'))
            },
            'mode_config': {
                'description': mode_config.get('description'),
                'symbol_routing': mode_config.get('symbol_routing', {}),
                'risk_limits': mode_config.get('risk_limits', {})
            }
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get detailed provider status"""
        return self.di_container.health_check_all_providers()
    
    def switch_mode(self, new_mode: str):
        """Switch trading mode and reinitialize components"""
        logger.info(f"Switching to {new_mode} mode")
        
        # Switch mode in DI container
        self.di_container.switch_mode(new_mode)
        
        # Reinitialize components with new mode
        self._initialize_components()
        
        logger.info(f"Successfully switched to {new_mode} mode")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk management metrics"""
        return self.risk_manager.get_risk_metrics()
    
    def get_signal_by_id(self, signal_id: str) -> Optional[TradingSignal]:
        """Get signal by ID"""
        for signal in self.active_signals:
            if signal.id == signal_id:
                return signal
        return None
    
    def get_recent_signals(self, limit: int = 20) -> List[TradingSignal]:
        """Get recent signals for debugging"""
        return self.active_signals[-limit:] if len(self.active_signals) > limit else self.active_signals
    
    def get_recent_executions(self, limit: int = 10) -> List[TradingSignal]:
        """Get recent executed signals"""
        executed_signals = self.get_executed_signals()
        executed_signals.sort(key=lambda s: s.execution_time or s.timestamp, reverse=True)
        return executed_signals[:limit]
    
    def _serialize_provider_health(self, health_obj) -> Dict[str, Any]:
        """Serialize provider health object for JSON response"""
        if health_obj is None:
            return {"status": "unavailable", "message": "Provider not available"}
        
        # Handle different types of health objects
        if hasattr(health_obj, 'status'):
            # ProviderHealthCheck or similar object
            result = {
                "status": health_obj.status.value if hasattr(health_obj.status, 'value') else str(health_obj.status),
                "timestamp": health_obj.timestamp.isoformat() if hasattr(health_obj, 'timestamp') and health_obj.timestamp else None,
                "message": getattr(health_obj, 'message', ''),
                "last_check": getattr(health_obj, 'last_check', None),
                "response_time": getattr(health_obj, 'response_time', None)
            }
            return result
        
        # Handle raw ProviderStatus enum
        if hasattr(health_obj, 'value'):
            return {"status": health_obj.value, "message": "Provider status"}
        
        # Fallback for other objects
        return {"status": str(health_obj), "message": "Unknown provider format"}