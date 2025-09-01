import logging
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, List
from polygon import RESTClient

from config import api_config, BLOCK_REASONS

logger = logging.getLogger(__name__)

class MarketDataProvider:
    """Polygon.io market data integration"""
    
    def __init__(self):
        if not api_config.polygon_api_key:
            logger.error("Polygon API key not configured")
            self.client = None
        else:
            self.client = RESTClient(api_config.polygon_api_key)
            logger.info("Polygon.io client initialized")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        if not self.client:
            logger.error("Polygon client not available")
            return None
            
        try:
            # Get last trade
            trades = self.client.get_last_trade(symbol)
            if trades and hasattr(trades, 'price'):
                logger.info(f"Current price for {symbol}: ${trades.price}")
                return float(trades.price)
            
            # Fallback to previous close
            aggs = self.client.get_previous_close_agg(symbol)
            if aggs and len(aggs) > 0:
                price = float(aggs[0].close)
                logger.info(f"Previous close for {symbol}: ${price}")
                return price
                
            logger.warning(f"No price data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    def is_market_open(self) -> bool:
        """Check if the market is currently open"""
        try:
            # Get market status
            status = self.client.get_market_status()
            if status and hasattr(status, 'market'):
                is_open = status.market == 'open'
                logger.info(f"Market status: {'open' if is_open else 'closed'}")
                return is_open
                
        except Exception as e:
            logger.error(f"Error checking market status: {str(e)}")
        
        # Fallback: simple time-based check (US market hours)
        now = datetime.now(timezone.utc)
        # Convert to EST/EDT (approximate)
        est_hour = (now.hour - 5) % 24
        weekday = now.weekday()
        
        # Market open Mon-Fri 9:30 AM - 4:00 PM EST
        is_weekday = weekday < 5
        is_market_hours = 9.5 <= est_hour < 16
        
        is_open = is_weekday and is_market_hours
        logger.info(f"Fallback market check: {'open' if is_open else 'closed'}")
        return is_open
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate that a symbol is tradeable"""
        if not self.client:
            return False
            
        try:
            # Try to get ticker details
            ticker = self.client.get_ticker_details(symbol)
            if ticker and hasattr(ticker, 'active'):
                is_active = ticker.active
                logger.info(f"Symbol {symbol} validation: {'active' if is_active else 'inactive'}")
                return is_active
                
        except Exception as e:
            logger.warning(f"Error validating symbol {symbol}: {str(e)}")
            
        # If we can't validate, assume it's valid to avoid blocking legitimate trades
        return True
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get comprehensive market data for a symbol"""
        if not self.client:
            return {}
            
        try:
            data = {
                'symbol': symbol,
                'current_price': self.get_current_price(symbol),
                'market_open': self.is_market_open(),
                'valid_symbol': self.validate_symbol(symbol),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add volume data if available
            try:
                aggs = self.client.get_previous_close_agg(symbol)
                if aggs and len(aggs) > 0:
                    data['volume'] = aggs[0].volume
                    data['previous_close'] = aggs[0].close
            except:
                pass
                
            return data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                prices[symbol] = price
        return prices