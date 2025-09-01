import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from .models import TradingSignal, SignalStatus, OrderType, OrderSide
from .execution_mode_manager import ExecutionModeManager
from providers.base_providers import ExecutionProvider

logger = logging.getLogger(__name__)

class ModularExecutionRouter:
    """Execution router using injected execution provider"""
    
    def __init__(self, execution_provider: ExecutionProvider, mode_config: Dict[str, Any], execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.execution_provider = execution_provider
        self.mode_config = mode_config
        self.symbol_routing = mode_config.get("symbol_routing", {})
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        
        logger.info(f"Execution router initialized with provider: {execution_provider.provider_name}")
        
    def execute(self, signal: TradingSignal) -> TradingSignal:
        """
        Execute signal through the configured execution provider
        """
        logger.info(f"Routing signal {signal.id} for execution via {self.execution_provider.provider_name}")
        
        # Validate routing permissions
        if not self._validate_routing(signal):
            return signal  # Signal already marked as blocked
        
        # CRITICAL FIX: Handle paper trading mode execution
        is_execution_mode = self.execution_mode_manager.is_execution_mode()
        
        if not is_execution_mode:
            # Paper trading mode - simulate successful execution
            logger.info(f"PAPER TRADING EXECUTION: Signal {signal.id} simulated execution for {signal.symbol} {signal.side.value} {signal.quantity}@${signal.price}")
            
            signal.status = SignalStatus.EXECUTED
            signal.execution_price = signal.price
            signal.execution_time = datetime.now(timezone.utc)
            signal.venue = "paper_trading_simulation"
            
            # Add paper trading metadata
            signal.metadata.update({
                'execution': {
                    'provider': 'paper_trading_simulation',
                    'order_id': f'PAPER_{signal.id[:8]}',
                    'executed_quantity': signal.quantity,
                    'execution_price': signal.price,
                    'execution_time': signal.execution_time.isoformat(),
                    'metadata': {'mode': 'paper_trading', 'simulated': True}
                }
            })
            
            logger.info(f"PAPER TRADE EXECUTED: {signal.quantity} {signal.symbol} @ ${signal.execution_price}")
            return signal
        
        # Real execution mode - use actual provider
        try:
            signal.venue = self.execution_provider.provider_name
            
            # Route to appropriate execution method based on order type
            if signal.order_type == OrderType.MARKET:
                execution_result = self.execution_provider.execute_market_order(
                    signal.symbol, 
                    signal.side.value, 
                    signal.quantity
                )
            elif signal.order_type == OrderType.LIMIT:
                if not signal.price:
                    signal.status = SignalStatus.BLOCKED
                    signal.block_reason = "Limit order requires price"
                    return signal
                
                execution_result = self.execution_provider.execute_limit_order(
                    signal.symbol,
                    signal.side.value,
                    signal.quantity,
                    signal.price
                )
            elif signal.order_type == OrderType.STOP:
                if not signal.stop_price:
                    signal.status = SignalStatus.BLOCKED
                    signal.block_reason = "Stop order requires stop price"
                    return signal
                
                execution_result = self.execution_provider.execute_stop_order(
                    signal.symbol,
                    signal.side.value,
                    signal.quantity,
                    signal.stop_price
                )
            else:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"Unsupported order type: {signal.order_type}"
                return signal
            
            # Process execution result
            if execution_result.success:
                signal.status = SignalStatus.EXECUTED
                signal.execution_price = execution_result.execution_price or signal.price
                signal.execution_time = execution_result.execution_time or datetime.now(timezone.utc)
                
                # Enhance metadata with execution details
                signal.metadata.update({
                    'execution': {
                        'provider': self.execution_provider.provider_name,
                        'order_id': execution_result.order_id,
                        'executed_quantity': execution_result.executed_quantity,
                        'execution_price': execution_result.execution_price,
                        'execution_time': execution_result.execution_time.isoformat() if execution_result.execution_time else None,
                        'metadata': execution_result.metadata
                    }
                })
                
                logger.info(f"Signal {signal.id} executed successfully via {self.execution_provider.provider_name}: "
                           f"{signal.quantity} {signal.symbol} @ ${signal.execution_price}")
            else:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = execution_result.error_message or "Execution failed"
                
                # Add execution attempt metadata
                signal.metadata.update({
                    'execution_attempt': {
                        'provider': self.execution_provider.provider_name,
                        'error_message': execution_result.error_message,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'metadata': execution_result.metadata
                    }
                })
                
                logger.error(f"Signal {signal.id} execution failed: {execution_result.error_message}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error executing signal {signal.id} via {self.execution_provider.provider_name}: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Execution error: {str(e)}"
            
            signal.metadata.update({
                'execution_error': {
                    'provider': self.execution_provider.provider_name,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            })
            
            return signal
    
    def _validate_routing(self, signal: TradingSignal) -> bool:
        """Validate that signal can be routed to current execution provider"""
        try:
            # Classify the symbol
            symbol_type = self._classify_symbol(signal.symbol)
            
            # Check if symbol type is allowed in current mode
            allowed_venue = self.symbol_routing.get(symbol_type)
            
            if allowed_venue == "blocked":
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"Symbol type '{symbol_type}' is blocked in current trading mode"
                logger.warning(f"Signal {signal.id} blocked: {symbol_type} not allowed in current mode")
                return False
            
            # Check if current execution provider can handle this symbol type
            provider_name = self.execution_provider.provider_name.lower()
            
            # Provider capability mapping
            provider_capabilities = {
                'tradestation': ['stocks', 'etfs', 'options'],
                'defi': ['crypto'],
                # Add more providers and their capabilities as needed
            }
            
            supported_types = provider_capabilities.get(provider_name, [])
            
            if symbol_type not in supported_types and allowed_venue != "auto_route":
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"Provider {self.execution_provider.provider_name} cannot execute {symbol_type}"
                logger.warning(f"Signal {signal.id} blocked: provider capability mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating routing for signal {signal.id}: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Routing validation error: {str(e)}"
            return False
    
    def _classify_symbol(self, symbol: str) -> str:
        """Classify symbol type for routing decisions"""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        crypto_patterns = ['BTC', 'ETH', 'USDT', 'USDC', 'DOGE', 'ADA', 'DOT', 'LINK', 'UNI', 'AAVE']
        if any(crypto in symbol_upper for crypto in crypto_patterns):
            return "crypto"
        
        # ETF patterns (common ETF symbols)
        etf_patterns = ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG']
        if any(etf in symbol_upper for etf in etf_patterns) or symbol_upper.endswith('ETF'):
            return "etfs"
        
        # Options patterns (basic detection)
        if len(symbol) > 6 and any(char.isdigit() for char in symbol[-8:]):
            return "options"
        
        # Default to stocks for standard ticker symbols
        if len(symbol) <= 5 and symbol.isalpha():
            return "stocks"
        
        # If we can't classify, default to stocks
        logger.warning(f"Could not classify symbol {symbol}, defaulting to 'stocks'")
        return "stocks"
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution routing statistics"""
        stats = {
            'execution_provider': {
                'name': self.execution_provider.provider_name,
                'available': True
            },
            'mode_config': {
                'description': self.mode_config.get('description'),
                'symbol_routing': self.symbol_routing
            },
            'last_routing_time': datetime.now().isoformat()
        }
        
        # Add provider health check
        try:
            health_check = self.execution_provider.health_check()
            stats['execution_provider']['health'] = {
                'status': health_check.status.value,
                'response_time_ms': health_check.response_time_ms,
                'last_check': health_check.last_check.isoformat(),
                'error_message': health_check.error_message
            }
        except Exception as e:
            stats['execution_provider']['health_error'] = str(e)
        
        # Add account information if available
        try:
            balance = self.execution_provider.get_account_balance()
            positions = self.execution_provider.get_positions()
            
            stats['account_info'] = {
                'balance': balance,
                'positions_count': len(positions) if positions else 0,
                'top_positions': positions[:3] if positions else []  # Top 3 positions for display
            }
        except Exception as e:
            stats['account_info_error'] = str(e)
        
        return stats
    
    def get_provider_capabilities(self) -> Dict[str, Any]:
        """Get information about current execution provider capabilities"""
        provider_name = self.execution_provider.provider_name.lower()
        
        capabilities = {
            'tradestation': {
                'supported_symbols': ['stocks', 'etfs', 'options'],
                'order_types': ['market', 'limit', 'stop'],
                'features': ['real_time_execution', 'account_balance', 'positions', 'order_cancellation']
            },
            'defi': {
                'supported_symbols': ['crypto'],
                'order_types': ['market'],  # Typically swap-based
                'features': ['decentralized_execution', 'wallet_balance']
            }
        }
        
        return capabilities.get(provider_name, {
            'supported_symbols': ['unknown'],
            'order_types': ['market'],
            'features': ['basic_execution']
        })