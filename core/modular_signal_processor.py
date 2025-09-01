import logging
from datetime import datetime
from typing import Optional, Dict, Any

from .models import TradingSignal, SignalStatus
from providers.base_providers import PriceDataProvider, NewsProvider, AnalyticsProvider
from .execution_mode_manager import ExecutionModeManager

logger = logging.getLogger(__name__)

class ModularSignalProcessor:
    """Signal processor using injected providers"""
    
    def __init__(self, price_provider: PriceDataProvider, 
                 news_provider: Optional[NewsProvider] = None,
                 analytics_provider: Optional[AnalyticsProvider] = None,
                 mode_config: Optional[Dict[str, Any]] = None,
                 execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.price_provider = price_provider
        self.news_provider = news_provider
        self.analytics_provider = analytics_provider
        self.mode_config = mode_config or {}
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        
        logger.info(f"Signal processor initialized with providers: "
                   f"price={price_provider.provider_name}, "
                   f"news={news_provider.provider_name if news_provider else 'None'}, "
                   f"analytics={analytics_provider.provider_name if analytics_provider else 'None'}")
        
    def process(self, signal: TradingSignal) -> TradingSignal:
        """
        Process a trading signal through validation and enrichment pipeline
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
            
        # Step 4: Optional enrichment with news sentiment
        self._enhance_with_news_sentiment(signal)
        
        # Step 5: Optional enrichment with technical indicators
        self._enhance_with_technical_analysis(signal)
        
        # Step 6: Final signal validation
        if not self._validate_signal_parameters(signal):
            return signal  # Signal already marked as blocked
        
        logger.info(f"Signal {signal.id} successfully processed with price ${signal.price}")
        return signal
    
    def get_blocking_reason(self, signal: TradingSignal) -> str:
        """Get detailed blocking reason for debugging"""
        if signal.status == SignalStatus.BLOCKED:
            return getattr(signal, 'block_reason', 'Unknown blocking reason')
        return "Signal not blocked"
    
    def _validate_market_conditions(self, signal: TradingSignal) -> bool:
        """Validate current market conditions"""
        try:
            # CRITICAL FIX: Bypass market hours for paper trading/simulation mode
            is_execution_mode = self.execution_mode_manager.is_execution_mode()
            
            if not is_execution_mode:
                # Paper trading mode - allow 24/7 trading regardless of market hours
                logger.info(f"Signal {signal.id} market hours bypassed: PAPER TRADING MODE - 24/7 execution enabled")
                return True
                
            # Only check market hours in real execution mode
            if not self.price_provider.is_market_open():
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = "Market is closed for trading"
                logger.warning(f"Signal {signal.id} blocked: market closed (REAL EXECUTION MODE)")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Market validation error: {str(e)}"
            return False
    
    def _validate_symbol(self, signal: TradingSignal) -> bool:
        """Validate symbol is tradeable"""
        try:
            if not self.price_provider.validate_symbol(signal.symbol):
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"Invalid or inactive symbol: {signal.symbol}"
                logger.warning(f"Signal {signal.id} blocked: invalid symbol {signal.symbol}")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error validating symbol {signal.symbol}: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Symbol validation error: {str(e)}"
            return False
    
    def _enhance_with_market_data(self, signal: TradingSignal) -> bool:
        """Enhance signal with current market data"""
        try:
            market_data = self.price_provider.get_current_price(signal.symbol)
            
            if market_data is None:
                # Try fallback provider if available
                # This would be handled by the DI container in a more complete implementation
                signal.status = SignalStatus.BLOCKED
                signal.block_reason = f"No price data available for {signal.symbol}"
                logger.error(f"Could not get price for {signal.symbol}")
                return False
            
            # Update signal with market price if not provided
            if signal.price is None:
                signal.price = market_data.price
                logger.info(f"Updated signal {signal.id} with market price: ${market_data.price}")
            
            # Enhance metadata with market data
            signal.metadata.update({
                'market_data': {
                    'current_price': market_data.price,
                    'volume': market_data.volume,
                    'bid': market_data.bid,
                    'ask': market_data.ask,
                    'spread': market_data.spread,
                    'previous_close': market_data.previous_close,
                    'change_percent': market_data.change_percent,
                    'provider': market_data.metadata.get('provider'),
                    'timestamp': market_data.timestamp.isoformat()
                }
            })
            
            # Price quality checks
            if market_data.spread and market_data.spread > market_data.price * 0.05:  # 5% spread threshold
                logger.warning(f"Wide spread detected for {signal.symbol}: {market_data.spread}")
                signal.metadata['warnings'] = signal.metadata.get('warnings', [])
                signal.metadata['warnings'].append('wide_spread')
            
            return True
            
        except Exception as e:
            logger.error(f"Error enhancing signal with market data: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Market data error: {str(e)}"
            return False
    
    def _enhance_with_news_sentiment(self, signal: TradingSignal):
        """Optional enhancement with news sentiment data"""
        if not self.news_provider:
            return
        
        try:
            sentiment_score = self.news_provider.get_sentiment_score(signal.symbol)
            
            if sentiment_score is not None:
                signal.metadata['sentiment'] = {
                    'score': sentiment_score,
                    'provider': self.news_provider.provider_name,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add sentiment interpretation
                if sentiment_score > 0.3:
                    sentiment_label = 'bullish'
                elif sentiment_score < -0.3:
                    sentiment_label = 'bearish'
                else:
                    sentiment_label = 'neutral'
                
                signal.metadata['sentiment']['label'] = sentiment_label
                logger.info(f"Enhanced signal {signal.id} with sentiment: {sentiment_label} ({sentiment_score:.2f})")
                
        except Exception as e:
            logger.warning(f"Error getting sentiment data for {signal.symbol}: {e}")
            # Don't block signal for optional enhancement failures
    
    def _enhance_with_technical_analysis(self, signal: TradingSignal):
        """Optional enhancement with technical indicators"""
        if not self.analytics_provider:
            return
        
        try:
            # Get key technical indicators
            rsi = self.analytics_provider.get_rsi(signal.symbol)
            sma_20 = self.analytics_provider.get_moving_average(signal.symbol, 20, "sma")
            
            if rsi or sma_20:
                signal.metadata['technical_analysis'] = {}
                
                if rsi:
                    signal.metadata['technical_analysis']['rsi'] = {
                        'value': rsi.value,
                        'interpretation': rsi.metadata.get('interpretation'),
                        'timestamp': rsi.timestamp.isoformat()
                    }
                    
                if sma_20:
                    signal.metadata['technical_analysis']['sma_20'] = {
                        'value': sma_20.value,
                        'timestamp': sma_20.timestamp.isoformat()
                    }
                    
                    # Add price vs SMA comparison
                    if signal.price and sma_20.value:
                        price_vs_sma = ((signal.price - sma_20.value) / sma_20.value) * 100
                        signal.metadata['technical_analysis']['price_vs_sma_20'] = {
                            'percent_diff': round(price_vs_sma, 2),
                            'position': 'above' if price_vs_sma > 0 else 'below'
                        }
                
                signal.metadata['technical_analysis']['provider'] = self.analytics_provider.provider_name
                logger.info(f"Enhanced signal {signal.id} with technical indicators")
                
        except Exception as e:
            logger.warning(f"Error getting technical analysis for {signal.symbol}: {e}")
            # Don't block signal for optional enhancement failures
    
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
            
            # Additional validations based on market data
            market_data = signal.metadata.get('market_data', {})
            current_price = market_data.get('current_price')
            
            if current_price and signal.price:
                # Check for extreme price deviations (potential data errors)
                price_deviation = abs(signal.price - current_price) / current_price
                if price_deviation > 0.20:  # 20% deviation threshold
                    logger.warning(f"Large price deviation for {signal.symbol}: signal=${signal.price}, market=${current_price}")
                    signal.metadata['warnings'] = signal.metadata.get('warnings', [])
                    signal.metadata['warnings'].append('price_deviation')
            
            # Calculate and log position value
            position_value = signal.quantity * signal.price
            logger.info(f"Signal {signal.id} validated: {signal.symbol} {signal.side.value} {signal.quantity} @ ${signal.price} = ${position_value:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal parameters: {e}")
            signal.status = SignalStatus.BLOCKED
            signal.block_reason = f"Parameter validation error: {str(e)}"
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        stats = {
            'price_provider': {
                'name': self.price_provider.provider_name,
                'available': True
            },
            'optional_providers': {
                'news': self.news_provider.provider_name if self.news_provider else None,
                'analytics': self.analytics_provider.provider_name if self.analytics_provider else None
            },
            'last_processing_time': datetime.now().isoformat(),
            'mode_config': self.mode_config.get('description', 'Unknown')
        }
        
        # Add provider health checks
        try:
            stats['price_provider']['health'] = self.price_provider.health_check()
        except Exception as e:
            stats['price_provider']['health_error'] = str(e)
        
        return stats