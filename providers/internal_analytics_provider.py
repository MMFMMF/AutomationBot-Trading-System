import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import requests

from .base_providers import (
    AnalyticsProvider, TechnicalIndicator, ProviderHealthCheck, ProviderStatus,
    PriceDataProvider
)

logger = logging.getLogger(__name__)

class InternalAnalyticsProvider(AnalyticsProvider):
    """Internal technical analysis provider using basic calculations"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials
        self._price_cache = {}
        self._indicator_cache = {}
        self._cache_duration = timedelta(minutes=config.get("cache_duration_minutes", 5))
        self._last_health_check = None
        
        # We'll need a price data source for calculations
        self._price_provider = None  # Will be injected by DI container
    
    @property
    def provider_name(self) -> str:
        return "internal_ta"
    
    def set_price_provider(self, price_provider: PriceDataProvider):
        """Inject price data provider for calculations"""
        self._price_provider = price_provider
    
    def _get_historical_data(self, symbol: str, days: int = 30) -> Optional[List[float]]:
        """Get historical price data for calculations"""
        # In a real implementation, this would fetch historical data
        # For now, we'll simulate with some basic data or use a simple approach
        
        cache_key = f"{symbol}_{days}"
        if cache_key in self._price_cache:
            cached_data, timestamp = self._price_cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                return cached_data
        
        try:
            # For simulation, generate some sample price data
            # In production, this would fetch real historical data from Polygon or other source
            current_price = 100.0  # Default base price
            
            if self._price_provider:
                current_data = self._price_provider.get_current_price(symbol)
                if current_data:
                    current_price = current_data.price
            
            # Generate simulated historical data with some volatility
            np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
            returns = np.random.normal(0, 0.02, days)  # 2% daily volatility
            prices = [current_price]
            
            for i in range(days - 1):
                next_price = prices[-1] * (1 + returns[i])
                prices.append(max(next_price, 0.01))  # Ensure positive prices
            
            # Reverse to get chronological order (oldest first)
            prices.reverse()
            
            # Cache the result
            self._price_cache[cache_key] = (prices, datetime.now())
            
            return prices
            
        except Exception as e:
            logger.error(f"Error generating historical data for {symbol}: {e}")
            return None
    
    def get_rsi(self, symbol: str, period: int = 14) -> Optional[TechnicalIndicator]:
        """Calculate RSI indicator"""
        try:
            cache_key = f"rsi_{symbol}_{period}"
            if cache_key in self._indicator_cache:
                cached_indicator, timestamp = self._indicator_cache[cache_key]
                if datetime.now() - timestamp < self._cache_duration:
                    return cached_indicator
            
            # Get historical data
            prices = self._get_historical_data(symbol, period + 10)  # Extra data for calculation
            if not prices or len(prices) < period + 1:
                return None
            
            # Calculate RSI
            price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [max(change, 0) for change in price_changes]
            losses = [abs(min(change, 0)) for change in price_changes]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                rsi_value = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_value = 100 - (100 / (1 + rs))
            
            indicator = TechnicalIndicator(
                indicator_name="RSI",
                symbol=symbol.upper(),
                value=round(rsi_value, 2),
                timestamp=datetime.now(timezone.utc),
                period=period,
                metadata={
                    "provider": self.provider_name,
                    "avg_gain": avg_gain,
                    "avg_loss": avg_loss,
                    "interpretation": self._interpret_rsi(rsi_value)
                }
            )
            
            # Cache the result
            self._indicator_cache[cache_key] = (indicator, datetime.now())
            
            return indicator
            
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol}: {e}")
            return None
    
    def _interpret_rsi(self, rsi_value: float) -> str:
        """Interpret RSI value"""
        if rsi_value >= 70:
            return "overbought"
        elif rsi_value <= 30:
            return "oversold"
        else:
            return "neutral"
    
    def get_macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, TechnicalIndicator]]:
        """Calculate MACD indicators"""
        try:
            cache_key = f"macd_{symbol}_{fast}_{slow}_{signal}"
            if cache_key in self._indicator_cache:
                cached_indicators, timestamp = self._indicator_cache[cache_key]
                if datetime.now() - timestamp < self._cache_duration:
                    return cached_indicators
            
            # Get historical data
            prices = self._get_historical_data(symbol, slow + signal + 10)
            if not prices or len(prices) < slow + signal:
                return None
            
            # Calculate EMAs
            fast_ema = self._calculate_ema(prices, fast)
            slow_ema = self._calculate_ema(prices, slow)
            
            if not fast_ema or not slow_ema:
                return None
            
            # Calculate MACD line
            macd_line = fast_ema[-1] - slow_ema[-1]
            
            # For simplicity, use a basic signal line calculation
            signal_line = macd_line * 0.9  # Simplified signal line
            histogram = macd_line - signal_line
            
            indicators = {
                "macd": TechnicalIndicator(
                    indicator_name="MACD",
                    symbol=symbol.upper(),
                    value=round(macd_line, 4),
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "provider": self.provider_name,
                        "fast_period": fast,
                        "slow_period": slow
                    }
                ),
                "signal": TechnicalIndicator(
                    indicator_name="MACD_Signal",
                    symbol=symbol.upper(),
                    value=round(signal_line, 4),
                    timestamp=datetime.now(timezone.utc),
                    period=signal,
                    metadata={
                        "provider": self.provider_name
                    }
                ),
                "histogram": TechnicalIndicator(
                    indicator_name="MACD_Histogram",
                    symbol=symbol.upper(),
                    value=round(histogram, 4),
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "provider": self.provider_name,
                        "interpretation": "bullish" if histogram > 0 else "bearish"
                    }
                )
            }
            
            # Cache the result
            self._indicator_cache[cache_key] = (indicators, datetime.now())
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating MACD for {symbol}: {e}")
            return None
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[List[float]]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        try:
            alpha = 2.0 / (period + 1)
            ema_values = []
            
            # Start with simple moving average for the first value
            sma = sum(prices[:period]) / period
            ema_values.append(sma)
            
            # Calculate EMA for remaining values
            for i in range(period, len(prices)):
                ema = alpha * prices[i] + (1 - alpha) * ema_values[-1]
                ema_values.append(ema)
            
            return ema_values
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return None
    
    def get_moving_average(self, symbol: str, period: int, ma_type: str = "sma") -> Optional[TechnicalIndicator]:
        """Calculate moving average"""
        try:
            cache_key = f"{ma_type}_{symbol}_{period}"
            if cache_key in self._indicator_cache:
                cached_indicator, timestamp = self._indicator_cache[cache_key]
                if datetime.now() - timestamp < self._cache_duration:
                    return cached_indicator
            
            # Get historical data
            prices = self._get_historical_data(symbol, period + 5)
            if not prices or len(prices) < period:
                return None
            
            if ma_type.lower() == "sma":
                # Simple Moving Average
                ma_value = sum(prices[-period:]) / period
            elif ma_type.lower() == "ema":
                # Exponential Moving Average
                ema_values = self._calculate_ema(prices, period)
                if not ema_values:
                    return None
                ma_value = ema_values[-1]
            else:
                logger.error(f"Unsupported moving average type: {ma_type}")
                return None
            
            indicator = TechnicalIndicator(
                indicator_name=f"{ma_type.upper()}",
                symbol=symbol.upper(),
                value=round(ma_value, 4),
                timestamp=datetime.now(timezone.utc),
                period=period,
                metadata={
                    "provider": self.provider_name,
                    "ma_type": ma_type.upper()
                }
            )
            
            # Cache the result
            self._indicator_cache[cache_key] = (indicator, datetime.now())
            
            return indicator
            
        except Exception as e:
            logger.error(f"Error calculating {ma_type} for {symbol}: {e}")
            return None
    
    def get_bollinger_bands(self, symbol: str, period: int = 20, std_dev: int = 2) -> Optional[Dict[str, TechnicalIndicator]]:
        """Calculate Bollinger Bands"""
        try:
            cache_key = f"bb_{symbol}_{period}_{std_dev}"
            if cache_key in self._indicator_cache:
                cached_indicators, timestamp = self._indicator_cache[cache_key]
                if datetime.now() - timestamp < self._cache_duration:
                    return cached_indicators
            
            # Get historical data
            prices = self._get_historical_data(symbol, period + 5)
            if not prices or len(prices) < period:
                return None
            
            # Calculate middle band (SMA)
            recent_prices = prices[-period:]
            middle_band = sum(recent_prices) / period
            
            # Calculate standard deviation
            variance = sum((price - middle_band) ** 2 for price in recent_prices) / period
            std_deviation = variance ** 0.5
            
            # Calculate upper and lower bands
            upper_band = middle_band + (std_dev * std_deviation)
            lower_band = middle_band - (std_dev * std_deviation)
            
            indicators = {
                "upper": TechnicalIndicator(
                    indicator_name="BB_Upper",
                    symbol=symbol.upper(),
                    value=round(upper_band, 4),
                    timestamp=datetime.now(timezone.utc),
                    period=period,
                    metadata={
                        "provider": self.provider_name,
                        "std_dev": std_dev
                    }
                ),
                "middle": TechnicalIndicator(
                    indicator_name="BB_Middle",
                    symbol=symbol.upper(),
                    value=round(middle_band, 4),
                    timestamp=datetime.now(timezone.utc),
                    period=period,
                    metadata={
                        "provider": self.provider_name
                    }
                ),
                "lower": TechnicalIndicator(
                    indicator_name="BB_Lower",
                    symbol=symbol.upper(),
                    value=round(lower_band, 4),
                    timestamp=datetime.now(timezone.utc),
                    period=period,
                    metadata={
                        "provider": self.provider_name,
                        "std_dev": std_dev
                    }
                )
            }
            
            # Cache the result
            self._indicator_cache[cache_key] = (indicators, datetime.now())
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands for {symbol}: {e}")
            return None
    
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health"""
        start_time = datetime.now()
        
        try:
            # Test basic calculation capability
            test_prices = [100, 101, 99, 102, 98, 103, 97, 104]
            test_sma = sum(test_prices) / len(test_prices)
            
            if abs(test_sma - 100.5) < 0.1:  # Expected value
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                self._last_health_check = ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.CONNECTED,
                    last_check=end_time,
                    response_time_ms=response_time,
                    metadata={
                        "cache_size": len(self._indicator_cache),
                        "enabled_indicators": self.config.get("indicators_enabled", []),
                        "cache_duration_minutes": self.config.get("cache_duration_minutes", 5)
                    }
                )
            else:
                self._last_health_check = ProviderHealthCheck(
                    provider_name=self.provider_name,
                    status=ProviderStatus.ERROR,
                    last_check=start_time,
                    error_message="Calculation test failed"
                )
            
            return self._last_health_check
            
        except Exception as e:
            self._last_health_check = ProviderHealthCheck(
                provider_name=self.provider_name,
                status=ProviderStatus.ERROR,
                last_check=start_time,
                error_message=str(e)
            )
            
            return self._last_health_check