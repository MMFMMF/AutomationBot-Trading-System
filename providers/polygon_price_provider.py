import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from polygon import RESTClient

from .base_providers import (
    PriceDataProvider, MarketData, ProviderHealthCheck, ProviderStatus
)

logger = logging.getLogger(__name__)

class PolygonPriceProvider(PriceDataProvider):
    """Polygon.io price data provider implementation"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials
        self._client = None
        self._last_health_check = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Polygon.io client"""
        try:
            api_key = self.credentials.get("api_key")
            if not api_key:
                raise ValueError("Polygon.io API key not provided")
                
            self._client = RESTClient(api_key)
            logger.info("Polygon.io client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Polygon.io client: {e}")
            raise
    
    @property
    def provider_name(self) -> str:
        return "polygon_io"
    
    def get_current_price(self, symbol: str) -> Optional[MarketData]:
        """Get current market price for symbol"""
        if not self._client:
            return None
            
        try:
            # Get last trade
            trades = self._client.get_last_trade(symbol)
            
            if trades and hasattr(trades, 'price'):
                # Get additional data for enrichment
                volume = None
                previous_close = None
                
                try:
                    # Get previous close for context
                    aggs = self._client.get_previous_close_agg(symbol)
                    if aggs and len(aggs) > 0:
                        volume = aggs[0].volume
                        previous_close = aggs[0].close
                except:
                    pass  # Non-critical data
                
                # Calculate change percentage
                change_percent = None
                if previous_close and trades.price:
                    change_percent = ((trades.price - previous_close) / previous_close) * 100
                
                return MarketData(
                    symbol=symbol.upper(),
                    price=float(trades.price),
                    timestamp=datetime.now(timezone.utc),
                    volume=volume,
                    previous_close=previous_close,
                    change_percent=change_percent,
                    metadata={
                        "provider": self.provider_name,
                        "trade_timestamp": trades.participant_timestamp if hasattr(trades, 'participant_timestamp') else None,
                        "conditions": getattr(trades, 'conditions', None)
                    }
                )
            
            # Fallback to previous close if no recent trade
            try:
                aggs = self._client.get_previous_close_agg(symbol)
                if aggs and len(aggs) > 0:
                    agg_data = aggs[0]
                    return MarketData(
                        symbol=symbol.upper(),
                        price=float(agg_data.close),
                        timestamp=datetime.now(timezone.utc),
                        volume=agg_data.volume,
                        previous_close=agg_data.close,
                        metadata={
                            "provider": self.provider_name,
                            "source": "previous_close",
                            "high": agg_data.high,
                            "low": agg_data.low,
                            "open": agg_data.open
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get previous close for {symbol}: {e}")
            
            logger.warning(f"No price data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[MarketData]]:
        """Get prices for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                results[symbol] = self.get_current_price(symbol)
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")
                results[symbol] = None
                
        return results
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        if not self._client:
            return False
            
        try:
            # Get market status
            status = self._client.get_market_status()
            if status and hasattr(status, 'market'):
                is_open = status.market == 'open'
                logger.debug(f"Market status from Polygon: {'open' if is_open else 'closed'}")
                return is_open
                
        except Exception as e:
            logger.warning(f"Error checking market status: {e}")
        
        # Fallback: simple time-based check (US market hours)
        now = datetime.now(timezone.utc)
        # Convert to EST/EDT (approximate)
        est_hour = (now.hour - 5) % 24
        weekday = now.weekday()
        
        # Market open Mon-Fri 9:30 AM - 4:00 PM EST
        is_weekday = weekday < 5
        is_market_hours = 9.5 <= est_hour < 16
        
        is_open = is_weekday and is_market_hours
        logger.debug(f"Fallback market check: {'open' if is_open else 'closed'}")
        return is_open
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is tradeable"""
        if not self._client:
            return False
            
        try:
            # Try to get ticker details
            ticker = self._client.get_ticker_details(symbol)
            if ticker and hasattr(ticker, 'active'):
                is_active = ticker.active
                logger.debug(f"Symbol {symbol} validation: {'active' if is_active else 'inactive'}")
                return is_active
                
        except Exception as e:
            logger.warning(f"Error validating symbol {symbol}: {e}")
            
        # If we can't validate, assume it's valid to avoid blocking legitimate trades
        return True
    
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        start_time = datetime.now()
        
        try:
            if not self._client:
                return ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.ERROR,
                    last_check=start_time,
                    error_message="Client not initialized"
                )
            
            # Test with a simple API call
            test_symbol = "AAPL"  # Use a known symbol
            status = self._client.get_market_status()
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=ProviderStatus.CONNECTED,
                last_check=end_time,
                response_time_ms=response_time,
                metadata={
                    "market_status": getattr(status, 'market', 'unknown') if status else 'unknown',
                    "test_symbol": test_symbol
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