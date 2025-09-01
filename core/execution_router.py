import logging
from datetime import datetime
from typing import Dict, Optional

from .models import TradingSignal, SignalStatus
from config import trading_config, EXECUTION_VENUES, BLOCK_REASONS

logger = logging.getLogger(__name__)

class ExecutionRouter:
    """Route signals to appropriate execution venues based on operating mode"""
    
    def __init__(self):
        self.venue_handlers = {}
        self._initialize_venue_handlers()
    
    def _initialize_venue_handlers(self):
        """Initialize venue-specific execution handlers"""
        # Import venue handlers based on operating mode
        available_venues = EXECUTION_VENUES[trading_config.operating_mode]
        
        if 'tradestation' in available_venues:
            try:
                from .venues.tradestation_handler import TradeStationHandler
                self.venue_handlers['tradestation'] = TradeStationHandler()
                logger.info("TradeStation handler initialized")
            except ImportError as e:
                logger.error(f"Failed to initialize TradeStation handler: {e}")
        
        if 'defi' in available_venues:
            try:
                from .venues.defi_handler import DeFiHandler
                self.venue_handlers['defi'] = DeFiHandler()
                logger.info("DeFi handler initialized")
            except ImportError as e:
                logger.error(f"Failed to initialize DeFi handler: {e}")
        
        logger.info(f"Execution router initialized with venues: {list(self.venue_handlers.keys())}")
    
    def execute(self, signal: TradingSignal) -> TradingSignal:
        """
        Execute signal through appropriate venue
        Returns signal with execution status
        """
        logger.info(f"Routing signal {signal.id} for execution")
        
        # Determine target venue
        venue = self._select_venue(signal)
        if not venue:
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['VENUE_UNAVAILABLE']
            logger.error(f"No venue available for signal {signal.id}")
            return signal
        
        # Get venue handler
        handler = self.venue_handlers.get(venue)
        if not handler:
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['VENUE_UNAVAILABLE']
            logger.error(f"Handler not available for venue {venue}")
            return signal
        
        # Execute through venue
        try:
            signal.venue = venue
            executed_signal = handler.execute_trade(signal)
            
            if executed_signal.status == SignalStatus.EXECUTED:
                logger.info(f"Signal {signal.id} executed via {venue} at ${executed_signal.execution_price}")
            else:
                logger.warning(f"Signal {signal.id} blocked by {venue}: {executed_signal.block_reason}")
            
            return executed_signal
            
        except Exception as e:
            logger.error(f"Error executing signal {signal.id} via {venue}: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return signal
    
    def _select_venue(self, signal: TradingSignal) -> Optional[str]:
        """Select appropriate venue for signal execution"""
        available_venues = EXECUTION_VENUES[trading_config.operating_mode]
        
        # For now, use simple selection logic
        # In a real system, this could consider:
        # - Symbol type (stocks -> TradeStation, crypto -> DeFi)
        # - Venue availability/health
        # - Cost optimization
        # - Liquidity considerations
        
        if len(available_venues) == 1:
            return available_venues[0]
        
        # Multi-venue selection logic
        if 'tradestation' in available_venues:
            # Prefer TradeStation for traditional securities
            symbol_upper = signal.symbol.upper()
            if not any(crypto in symbol_upper for crypto in ['BTC', 'ETH', 'USDT', 'USDC']):
                return 'tradestation'
        
        if 'defi' in available_venues:
            # Use DeFi for crypto-related symbols
            symbol_upper = signal.symbol.upper()
            if any(crypto in symbol_upper for crypto in ['BTC', 'ETH', 'USDT', 'USDC']):
                return 'defi'
        
        # Default to first available venue
        return available_venues[0] if available_venues else None
    
    def get_venue_status(self) -> Dict[str, dict]:
        """Get status of all venue handlers"""
        status = {}
        for venue_name, handler in self.venue_handlers.items():
            try:
                status[venue_name] = handler.get_status()
            except Exception as e:
                status[venue_name] = {'error': str(e), 'available': False}
        
        return status
    
    def get_routing_stats(self) -> dict:
        """Get routing statistics"""
        return {
            'operating_mode': trading_config.operating_mode,
            'available_venues': list(self.venue_handlers.keys()),
            'venue_count': len(self.venue_handlers),
            'last_update': datetime.now().isoformat()
        }