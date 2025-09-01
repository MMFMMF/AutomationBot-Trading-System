import logging
from datetime import datetime
from typing import Optional

from .models import TradingSignal, SignalStatus
from .market_data import MarketDataProvider
from config import BLOCK_REASONS

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Process and validate trading signals before execution"""
    
    def __init__(self):
        self.market_data = MarketDataProvider()
        
    def process(self, signal: TradingSignal) -> TradingSignal:
        """
        Process a trading signal through validation pipeline
        Returns processed signal with updated status
        """
        logger.info(f"Processing signal {signal.id} for {signal.symbol}")
        
        # Step 1: Market validation
        if not self._validate_market_conditions(signal):
            return signal  # Signal already marked as blocked
        
        # Step 2: Symbol validation
        if not self._validate_symbol(signal):
            return signal  # Signal already marked as blocked
            
        # Step 3: Price validation and enhancement
        if not self._enhance_with_market_data(signal):
            return signal  # Signal already marked as blocked
            
        # Step 4: Final signal validation
        if not self._validate_signal_parameters(signal):
            return signal  # Signal already marked as blocked
        
        logger.info(f"Signal {signal.id} successfully processed")
        return signal
    
    def _validate_market_conditions(self, signal: TradingSignal) -> bool:
        """Validate current market conditions"""
        try:
            if not self.market_data.is_market_open():
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = BLOCK_REASONS['MARKET_CLOSED']
                logger.warning(f"Signal {signal.id} blocked: market closed")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return False
    
    def _validate_symbol(self, signal: TradingSignal) -> bool:
        """Validate symbol is tradeable"""
        try:
            if not self.market_data.validate_symbol(signal.symbol):
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = BLOCK_REASONS['INVALID_SYMBOL']
                logger.warning(f"Signal {signal.id} blocked: invalid symbol {signal.symbol}")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error validating symbol {signal.symbol}: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return False
    
    def _enhance_with_market_data(self, signal: TradingSignal) -> bool:
        """Enhance signal with current market data"""
        try:
            current_price = self.market_data.get_current_price(signal.symbol)
            
            if current_price is None:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = BLOCK_REASONS['API_ERROR']
                logger.error(f"Could not get price for {signal.symbol}")
                return False
            
            # Update signal with market price if not provided
            if signal.price is None:
                signal.price = current_price
                logger.info(f"Updated signal {signal.id} with market price: ${current_price}")
            
            # Store market data in metadata
            signal.metadata.update({
                'market_price': current_price,
                'price_timestamp': datetime.now().isoformat(),
                'market_open': True
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error enhancing signal with market data: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return False
    
    def _validate_signal_parameters(self, signal: TradingSignal) -> bool:
        """Final validation of signal parameters"""
        try:
            # Validate quantity
            if signal.quantity <= 0:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = "Invalid quantity: must be positive"
                logger.warning(f"Signal {signal.id} blocked: invalid quantity {signal.quantity}")
                return False
            
            # Validate price for limit orders
            if signal.price and signal.price <= 0:
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = "Invalid price: must be positive"
                logger.warning(f"Signal {signal.id} blocked: invalid price {signal.price}")
                return False
            
            # Calculate position value for logging
            position_value = signal.quantity * signal.price
            logger.info(f"Signal {signal.id} validated: ${position_value:.2f} position")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal parameters: {str(e)}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = BLOCK_REASONS['API_ERROR']
            return False
    
    def get_processing_stats(self) -> dict:
        """Get signal processing statistics"""
        return {
            'market_data_available': self.market_data.client is not None,
            'last_processing_time': datetime.now().isoformat()
        }