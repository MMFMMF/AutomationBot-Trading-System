from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import logging

from ..models import TradingSignal

logger = logging.getLogger(__name__)

class BaseVenueHandler(ABC):
    """Base class for all venue execution handlers"""
    
    def __init__(self, venue_name: str):
        self.venue_name = venue_name
        self.connected = False
        self.last_connection_check = None
        
    @abstractmethod
    def execute_trade(self, signal: TradingSignal) -> TradingSignal:
        """Execute a trade through this venue"""
        pass
    
    @abstractmethod
    def get_account_status(self) -> Dict[str, Any]:
        """Get current account status"""
        pass
    
    @abstractmethod
    def check_connection(self) -> bool:
        """Check if connection to venue is healthy"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get venue status"""
        return {
            'venue_name': self.venue_name,
            'connected': self.connected,
            'last_connection_check': self.last_connection_check.isoformat() if self.last_connection_check else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_connection_status(self) -> bool:
        """Update and return connection status"""
        self.connected = self.check_connection()
        self.last_connection_check = datetime.now()
        logger.info(f"{self.venue_name} connection status: {'connected' if self.connected else 'disconnected'}")
        return self.connected