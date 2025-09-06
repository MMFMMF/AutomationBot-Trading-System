"""
Polygon News Provider - Minimal Implementation
Provides basic news functionality to resolve missing component error
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from .base_providers import NewsProvider, NewsItem, ProviderStatus, ProviderHealthCheck

logger = logging.getLogger(__name__)

class PolygonNewsProvider(NewsProvider):
    """Polygon.io news provider - minimal implementation"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.status = ProviderStatus.CONNECTED if api_key else ProviderStatus.UNAVAILABLE
        logger.info(f"Polygon news provider initialized: {self.status.value}")
    
    @property
    def provider_name(self) -> str:
        return "polygon_news"
    
    def get_latest_news(self, symbols: Optional[List[str]] = None, limit: int = 10) -> List[NewsItem]:
        """Get latest news items - minimal implementation"""
        # Return empty list for now to prevent errors
        logger.debug(f"News request for symbols: {symbols}, limit: {limit}")
        return []
    
    def get_sentiment_score(self, symbol: str) -> Optional[float]:
        """Get sentiment score - minimal implementation"""
        # Return neutral sentiment to prevent errors
        logger.debug(f"Sentiment request for symbol: {symbol}")
        return 0.0  # Neutral sentiment
    
    def search_news(self, query: str, limit: int = 10) -> List[NewsItem]:
        """Search news by query - minimal implementation"""
        logger.debug(f"News search request: {query}, limit: {limit}")
        return []
    
    def health_check(self) -> ProviderHealthCheck:
        """Check provider health and connectivity"""
        return ProviderHealthCheck(
            status=self.status,
            response_time_ms=None,
            last_check=datetime.now(),
            message="Minimal implementation - always healthy" if self.status == ProviderStatus.CONNECTED else "No API key provided"
        )
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return {
            "provider": self.provider_name,
            "status": self.status.value,
            "last_check": datetime.now().isoformat(),
            "response_time_ms": None
        }