from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class ProviderStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected" 
    ERROR = "error"
    UNAVAILABLE = "unavailable"

@dataclass
class MarketData:
    """Normalized market data structure"""
    symbol: str
    price: float
    timestamp: datetime
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    previous_close: Optional[float] = None
    change_percent: Optional[float] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ExecutionResult:
    """Normalized execution result structure"""
    success: bool
    order_id: Optional[str] = None
    execution_price: Optional[float] = None
    executed_quantity: Optional[float] = None
    execution_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class NewsItem:
    """Normalized news/sentiment data structure"""
    title: str
    content: str
    timestamp: datetime
    source: str
    symbols: List[str]
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    relevance_score: Optional[float] = None  # 0.0 to 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TechnicalIndicator:
    """Normalized technical indicator data"""
    indicator_name: str
    symbol: str
    value: float
    timestamp: datetime
    period: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ProviderHealthCheck:
    """Provider health status"""
    provider_name: str
    status: ProviderStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# =============================================================================
# INTERFACE CONTRACTS
# =============================================================================

class PriceDataProvider(ABC):
    """Base interface for all market data providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[MarketData]:
        """Get current market price for symbol"""
        pass
    
    @abstractmethod
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[MarketData]]:
        """Get prices for multiple symbols"""
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        pass
    
    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is tradeable"""
        pass
    
    @abstractmethod
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        pass

class ExecutionProvider(ABC):
    """Base interface for all trade execution providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def execute_market_order(self, symbol: str, side: str, quantity: float) -> ExecutionResult:
        """Execute market order"""
        pass
    
    @abstractmethod
    def execute_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        """Execute limit order"""
        pass
    
    @abstractmethod
    def execute_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> ExecutionResult:
        """Execute stop order"""
        pass
    
    @abstractmethod
    def get_account_balance(self) -> Optional[float]:
        """Get available account balance"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        pass

class NewsProvider(ABC):
    """Base interface for news/sentiment data providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def get_latest_news(self, symbols: Optional[List[str]] = None, limit: int = 10) -> List[NewsItem]:
        """Get latest news items"""
        pass
    
    @abstractmethod
    def get_sentiment_score(self, symbol: str) -> Optional[float]:
        """Get sentiment score for symbol (-1.0 to 1.0)"""
        pass
    
    @abstractmethod
    def search_news(self, query: str, limit: int = 10) -> List[NewsItem]:
        """Search news by query"""
        pass
    
    @abstractmethod
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        pass

class AnalyticsProvider(ABC):
    """Base interface for technical analysis providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def get_rsi(self, symbol: str, period: int = 14) -> Optional[TechnicalIndicator]:
        """Get RSI indicator"""
        pass
    
    @abstractmethod
    def get_macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, TechnicalIndicator]]:
        """Get MACD indicators (macd, signal, histogram)"""
        pass
    
    @abstractmethod
    def get_moving_average(self, symbol: str, period: int, ma_type: str = "sma") -> Optional[TechnicalIndicator]:
        """Get moving average (SMA, EMA, etc.)"""
        pass
    
    @abstractmethod
    def get_bollinger_bands(self, symbol: str, period: int = 20, std_dev: int = 2) -> Optional[Dict[str, TechnicalIndicator]]:
        """Get Bollinger Bands (upper, middle, lower)"""
        pass
    
    @abstractmethod
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        pass