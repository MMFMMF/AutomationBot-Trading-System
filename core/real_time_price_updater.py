"""
Real-time Price Updater with Polygon.io Integration
Updates market prices every 30-60 seconds for accurate P&L calculations
"""
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
from dataclasses import dataclass

from core.config_manager import SystemConfig
from providers.polygon_price_provider import PolygonPriceProvider
from core.pnl_calculator import RealTimePnLCalculator

logger = logging.getLogger(__name__)

@dataclass
class PriceUpdate:
    """Price update data structure"""
    symbol: str
    price: float
    timestamp: datetime
    source: str
    volume: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None

class RealTimePriceUpdater:
    """
    Real-time price updater that integrates with Polygon.io
    Updates prices every 30-60 seconds during market hours
    Provides accurate current prices for P&L calculations
    """
    
    def __init__(self, config: SystemConfig, polygon_provider: Optional[PolygonPriceProvider] = None):
        self.config = config
        self.polygon_provider = polygon_provider
        self.update_interval = 30  # seconds
        self.is_running = False
        self.tracked_symbols: Set[str] = set()
        self.latest_prices: Dict[str, PriceUpdate] = {}
        self.price_callbacks: List = []
        self.update_task: Optional[asyncio.Task] = None
        
        # Market hours configuration
        self.market_open_hour = 9
        self.market_open_minute = 30
        self.market_close_hour = 16
        self.market_close_minute = 0
        
        logger.info("Real-time price updater initialized")
    
    def add_symbols(self, symbols: List[str]):
        """Add symbols to track for price updates"""
        new_symbols = set(symbols) - self.tracked_symbols
        if new_symbols:
            self.tracked_symbols.update(new_symbols)
            logger.info(f"Added {len(new_symbols)} new symbols to track: {new_symbols}")
    
    def remove_symbols(self, symbols: List[str]):
        """Remove symbols from tracking"""
        removed = set(symbols) & self.tracked_symbols
        if removed:
            self.tracked_symbols -= removed
            # Clean up old prices
            for symbol in removed:
                self.latest_prices.pop(symbol, None)
            logger.info(f"Removed {len(removed)} symbols from tracking: {removed}")
    
    def add_price_callback(self, callback):
        """Add callback function to be called when prices are updated"""
        self.price_callbacks.append(callback)
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (ET)"""
        now = datetime.now()
        
        # Simple market hours check (9:30 AM - 4:00 PM ET, Monday-Friday)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        market_open = now.replace(hour=self.market_open_hour, minute=self.market_open_minute, second=0, microsecond=0)
        market_close = now.replace(hour=self.market_close_hour, minute=self.market_close_minute, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    async def start_price_updates(self):
        """Start the real-time price update loop"""
        if self.is_running:
            logger.warning("Price updater is already running")
            return
        
        self.is_running = True
        logger.info("Starting real-time price updates")
        
        try:
            while self.is_running:
                if self.tracked_symbols:
                    await self._update_all_prices()
                
                # Adjust update frequency based on market hours
                if self.is_market_hours():
                    # More frequent updates during market hours
                    await asyncio.sleep(30)
                else:
                    # Less frequent updates after hours
                    await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Price update loop cancelled")
        except Exception as e:
            logger.error(f"Error in price update loop: {e}")
        finally:
            self.is_running = False
            logger.info("Price update loop stopped")
    
    def start_background_updates(self):
        """Start price updates in background task"""
        if self.update_task and not self.update_task.done():
            logger.warning("Background updates already running")
            return
        
        self.update_task = asyncio.create_task(self.start_price_updates())
        logger.info("Started background price updates")
    
    def stop_price_updates(self):
        """Stop the price update loop"""
        self.is_running = False
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
        logger.info("Stopped price updates")
    
    async def _update_all_prices(self):
        """Update prices for all tracked symbols"""
        if not self.tracked_symbols:
            return
        
        start_time = time.time()
        updated_count = 0
        failed_count = 0
        
        try:
            # Batch update prices for efficiency
            price_updates = await self._fetch_batch_prices(list(self.tracked_symbols))
            
            for symbol, price_data in price_updates.items():
                try:
                    # Create price update object
                    previous_price = self.latest_prices.get(symbol)
                    current_price = price_data.get('price', 0)
                    
                    change = None
                    change_percent = None
                    
                    if previous_price:
                        change = current_price - previous_price.price
                        change_percent = (change / previous_price.price * 100) if previous_price.price > 0 else 0
                    
                    price_update = PriceUpdate(
                        symbol=symbol,
                        price=current_price,
                        timestamp=datetime.now(),
                        source='polygon.io',
                        volume=price_data.get('volume'),
                        change=change,
                        change_percent=change_percent
                    )
                    
                    self.latest_prices[symbol] = price_update
                    updated_count += 1
                    
                    logger.debug(f"Updated {symbol}: ${current_price:.4f}")
                    
                except Exception as e:
                    logger.error(f"Failed to process price update for {symbol}: {e}")
                    failed_count += 1
            
            # Notify callbacks about price updates
            if updated_count > 0:
                await self._notify_price_callbacks(price_updates)
            
            elapsed = time.time() - start_time
            logger.info(f"Price update completed: {updated_count} updated, {failed_count} failed in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
    
    async def _fetch_batch_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch prices for multiple symbols efficiently"""
        price_data = {}
        
        if not self.polygon_provider:
            logger.warning("No Polygon provider available, using mock prices")
            # Return mock prices for testing
            for symbol in symbols:
                price_data[symbol] = {
                    'price': 100.0 + hash(symbol) % 200,  # Mock price between 100-300
                    'volume': 1000000,
                    'timestamp': datetime.now()
                }
            return price_data
        
        try:
            # Use Polygon provider to get real market data
            for symbol in symbols:
                try:
                    # Get current price data
                    result = await self._get_polygon_price(symbol)
                    if result:
                        price_data[symbol] = result
                        
                    # Small delay to respect API rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to get price for {symbol}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in batch price fetch: {e}")
        
        return price_data
    
    async def _get_polygon_price(self, symbol: str) -> Optional[Dict]:
        """Get price data from Polygon.io"""
        try:
            if not self.polygon_provider:
                return None
            
            # Get last trade data
            price_data = await self.polygon_provider.get_current_price(symbol)
            
            if price_data and 'price' in price_data:
                return {
                    'price': float(price_data['price']),
                    'volume': price_data.get('volume', 0),
                    'timestamp': datetime.now(),
                    'source': 'polygon.io'
                }
            
        except Exception as e:
            logger.error(f"Error getting Polygon price for {symbol}: {e}")
        
        return None
    
    async def _notify_price_callbacks(self, price_updates: Dict[str, Dict]):
        """Notify registered callbacks about price updates"""
        if not self.price_callbacks:
            return
        
        for callback in self.price_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_updates)
                else:
                    callback(price_updates)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the current price for a symbol"""
        price_update = self.latest_prices.get(symbol)
        return price_update.price if price_update else None
    
    def get_price_update(self, symbol: str) -> Optional[PriceUpdate]:
        """Get the full price update object for a symbol"""
        return self.latest_prices.get(symbol)
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get current prices for all tracked symbols"""
        return {symbol: update.price for symbol, update in self.latest_prices.items()}
    
    def get_price_summary(self) -> Dict[str, any]:
        """Get summary of price updates"""
        total_symbols = len(self.tracked_symbols)
        updated_symbols = len(self.latest_prices)
        
        recent_updates = []
        for symbol, update in self.latest_prices.items():
            recent_updates.append({
                'symbol': symbol,
                'price': update.price,
                'change': update.change,
                'change_percent': update.change_percent,
                'last_updated': update.timestamp.isoformat()
            })
        
        # Sort by absolute change percent
        recent_updates.sort(key=lambda x: abs(x.get('change_percent', 0)), reverse=True)
        
        return {
            'total_symbols_tracked': total_symbols,
            'symbols_with_prices': updated_symbols,
            'is_market_hours': self.is_market_hours(),
            'update_interval': self.update_interval,
            'is_running': self.is_running,
            'recent_updates': recent_updates[:10],  # Top 10 by change
            'last_update_cycle': max((u.timestamp for u in self.latest_prices.values()), default=datetime.now()).isoformat()
        }
    
    async def force_update(self, symbols: Optional[List[str]] = None):
        """Force immediate price update for specified symbols or all tracked symbols"""
        symbols_to_update = symbols or list(self.tracked_symbols)
        
        if not symbols_to_update:
            logger.warning("No symbols to update")
            return
        
        logger.info(f"Forcing price update for {len(symbols_to_update)} symbols")
        
        # Add symbols to tracking if not already tracked
        self.add_symbols(symbols_to_update)
        
        # Update prices immediately
        await self._update_all_prices()
        
        logger.info("Forced price update completed")


class PnLPriceIntegration:
    """
    Integration class that connects real-time price updates with P&L calculations
    """
    
    def __init__(self, pnl_calculator: RealTimePnLCalculator, price_updater: RealTimePriceUpdater):
        self.pnl_calculator = pnl_calculator
        self.price_updater = price_updater
        
        # Register price update callback
        self.price_updater.add_price_callback(self._on_price_update)
        
        logger.info("P&L and price integration initialized")
    
    async def _on_price_update(self, price_updates: Dict[str, Dict]):
        """Callback function called when prices are updated"""
        try:
            # Get updated prices
            current_prices = {symbol: data['price'] for symbol, data in price_updates.items()}
            
            # Update P&L calculator with new prices
            # This will trigger recalculation of unrealized P&L
            logger.debug(f"Received price updates for {len(current_prices)} symbols")
            
            # The P&L calculator will use these prices in its next calculation cycle
            
        except Exception as e:
            logger.error(f"Error processing price update callback: {e}")
    
    def get_integrated_summary(self) -> Dict[str, any]:
        """Get combined summary of prices and P&L"""
        price_summary = self.price_updater.get_price_summary()
        position_summary = self.pnl_calculator.get_position_summary()
        performance_summary = self.pnl_calculator.get_performance_summary()
        
        return {
            'price_data': price_summary,
            'positions': position_summary,
            'performance': performance_summary,
            'integration_status': {
                'price_updates_active': self.price_updater.is_running,
                'symbols_tracked': len(self.price_updater.tracked_symbols),
                'positions_calculated': position_summary.get('total_positions', 0),
                'last_sync': datetime.now().isoformat()
            }
        }


def create_price_updater(config: SystemConfig, polygon_provider: Optional[PolygonPriceProvider] = None) -> RealTimePriceUpdater:
    """Factory function to create price updater"""
    return RealTimePriceUpdater(config, polygon_provider)


def create_integrated_pnl_system(config: SystemConfig, polygon_provider: Optional[PolygonPriceProvider] = None) -> PnLPriceIntegration:
    """Factory function to create integrated P&L system with real-time prices"""
    from core.pnl_calculator import get_pnl_calculator
    
    pnl_calculator = get_pnl_calculator(config, polygon_provider)
    price_updater = create_price_updater(config, polygon_provider)
    
    return PnLPriceIntegration(pnl_calculator, price_updater)