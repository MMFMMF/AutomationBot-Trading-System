import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .base_providers import ExecutionProvider, ExecutionResult, ProviderHealthCheck, ProviderStatus
from .tradestation_executor import TradeStationExecutor
from .defi_executor import DeFiExecutor

logger = logging.getLogger(__name__)

class AutoRouter(ExecutionProvider):
    """Intelligent execution router that automatically selects between TradeStation and DeFi"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials
        self._last_health_check = None
        
        # Initialize both execution providers
        try:
            self.tradestation = TradeStationExecutor(
                config.get('tradestation', {}), 
                credentials.get('tradestation', {})
            )
            logger.info("TradeStation executor initialized for auto-routing")
        except Exception as e:
            logger.warning(f"TradeStation executor failed to initialize: {e}")
            self.tradestation = None
            
        try:
            self.defi = DeFiExecutor(
                config.get('defi', {}), 
                credentials.get('defi', {})
            )
            logger.info("DeFi executor initialized for auto-routing")
        except Exception as e:
            logger.warning(f"DeFi executor failed to initialize: {e}")
            self.defi = None
        
        # Symbol routing configuration
        self.symbol_routing = config.get('symbol_routing', {
            'stocks': 'tradestation',
            'etfs': 'tradestation', 
            'options': 'tradestation',
            'crypto': 'defi'
        })
        
        logger.info("Auto-router initialized with intelligent execution routing")
    
    @property
    def provider_name(self) -> str:
        return "auto_route"
    
    def _determine_venue(self, symbol: str) -> str:
        """Determine which venue to route the symbol to"""
        symbol = symbol.upper()
        
        # Crypto symbols (common patterns)
        crypto_patterns = ['BTC', 'ETH', 'USDC', 'USDT', 'BNB', 'SOL', 'ADA', 'DOT', 'AVAX']
        if any(pattern in symbol for pattern in crypto_patterns):
            return 'defi'
        
        # ETF symbols (common patterns)
        etf_patterns = ['SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND']
        if any(pattern in symbol for pattern in etf_patterns):
            return 'tradestation'
        
        # Options symbols (contain option indicators)
        if any(indicator in symbol for indicator in ['C', 'P']) and len(symbol) > 5:
            return 'tradestation'
        
        # Default stocks to TradeStation
        return 'tradestation'
    
    def _get_executor(self, venue: str) -> Optional[ExecutionProvider]:
        """Get the appropriate executor for the venue"""
        if venue == 'tradestation' and self.tradestation:
            return self.tradestation
        elif venue == 'defi' and self.defi:
            return self.defi
        else:
            return None
    
    def execute_market_order(self, symbol: str, side: str, quantity: float) -> ExecutionResult:
        """Route market order to appropriate venue"""
        try:
            venue = self._determine_venue(symbol)
            executor = self._get_executor(venue)
            
            if not executor:
                return ExecutionResult(
                    success=False,
                    error_message=f"No available executor for venue '{venue}' (symbol: {symbol})"
                )
            
            logger.info(f"Routing {symbol} {side} order to {venue}")
            result = executor.execute_market_order(symbol, side, quantity)
            
            # Add routing metadata
            if result.metadata is None:
                result.metadata = {}
            result.metadata['routing_venue'] = venue
            result.metadata['router'] = self.provider_name
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-routing error for {symbol}: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Auto-routing failed: {str(e)}"
            )
    
    def execute_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        """Route limit order to appropriate venue"""
        try:
            venue = self._determine_venue(symbol)
            executor = self._get_executor(venue)
            
            if not executor:
                return ExecutionResult(
                    success=False,
                    error_message=f"No available executor for venue '{venue}' (symbol: {symbol})"
                )
            
            logger.info(f"Routing {symbol} {side} limit order to {venue}")
            result = executor.execute_limit_order(symbol, side, quantity, price)
            
            # Add routing metadata
            if result.metadata is None:
                result.metadata = {}
            result.metadata['routing_venue'] = venue
            result.metadata['router'] = self.provider_name
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-routing error for {symbol}: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Auto-routing failed: {str(e)}"
            )
    
    def execute_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> ExecutionResult:
        """Route stop order to appropriate venue"""
        try:
            venue = self._determine_venue(symbol)
            executor = self._get_executor(venue)
            
            if not executor:
                return ExecutionResult(
                    success=False,
                    error_message=f"No available executor for venue '{venue}' (symbol: {symbol})"
                )
            
            logger.info(f"Routing {symbol} {side} stop order to {venue}")
            result = executor.execute_stop_order(symbol, side, quantity, stop_price)
            
            # Add routing metadata
            if result.metadata is None:
                result.metadata = {}
            result.metadata['routing_venue'] = venue
            result.metadata['router'] = self.provider_name
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-routing error for {symbol}: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"Auto-routing failed: {str(e)}"
            )
    
    def get_account_balance(self) -> Optional[float]:
        """Get combined account balance from all venues"""
        total_balance = 0.0
        
        if self.tradestation:
            ts_balance = self.tradestation.get_account_balance()
            if ts_balance:
                total_balance += ts_balance
        
        if self.defi:
            defi_balance = self.defi.get_account_balance()
            if defi_balance:
                total_balance += defi_balance
        
        return total_balance if total_balance > 0 else None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get combined positions from all venues"""
        all_positions = []
        
        if self.tradestation:
            ts_positions = self.tradestation.get_positions()
            for pos in ts_positions:
                pos['venue'] = 'tradestation'
            all_positions.extend(ts_positions)
        
        if self.defi:
            defi_positions = self.defi.get_positions()
            for pos in defi_positions:
                pos['venue'] = 'defi'
            all_positions.extend(defi_positions)
        
        return all_positions
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (attempt on both venues)"""
        success = False
        
        if self.tradestation:
            if self.tradestation.cancel_order(order_id):
                success = True
        
        if self.defi:
            if self.defi.cancel_order(order_id):
                success = True
        
        return success
    
    def health_check(self) -> ProviderHealthCheck:
        """Check health of both underlying providers"""
        start_time = datetime.now()
        
        try:
            ts_health = None
            defi_health = None
            
            if self.tradestation:
                ts_health = self.tradestation.health_check()
            
            if self.defi:
                defi_health = self.defi.health_check()
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Determine overall status
            if ts_health and ts_health.status == ProviderStatus.CONNECTED:
                if defi_health and defi_health.status == ProviderStatus.CONNECTED:
                    status = ProviderStatus.CONNECTED
                    error_message = None
                else:
                    status = ProviderStatus.DEGRADED
                    error_message = "DeFi executor unavailable"
            elif defi_health and defi_health.status == ProviderStatus.CONNECTED:
                status = ProviderStatus.DEGRADED
                error_message = "TradeStation executor unavailable"
            else:
                status = ProviderStatus.ERROR
                error_message = "Both executors unavailable"
            
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=status,
                last_check=end_time,
                response_time_ms=response_time,
                error_message=error_message,
                metadata={
                    "tradestation_status": ts_health.status.value if ts_health else "unavailable",
                    "defi_status": defi_health.status.value if defi_health else "unavailable",
                    "routing_config": self.symbol_routing
                }
            )
            
            return self._last_health_check
            
        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=ProviderStatus.ERROR,
                last_check=end_time,
                response_time_ms=response_time,
                error_message=str(e)
            )
            
            return self._last_health_check