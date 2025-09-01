from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class SignalStatus(Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    EXECUTED = "executed"
    BLOCKED = "blocked"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

@dataclass
class TradingSignal:
    """Represents a trading signal received by the system"""
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = None
    status: SignalStatus = SignalStatus.RECEIVED
    block_reason: Optional[str] = None
    venue: Optional[str] = None
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Position:
    """Represents a current trading position"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    venue: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class AccountStatus:
    """Represents current account status"""
    total_equity: float
    available_cash: float
    day_pnl: float
    total_pnl: float
    positions: list[Position]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class RiskCheck:
    """Represents a risk check result"""
    passed: bool
    reason: Optional[str] = None
    max_allowed_quantity: Optional[float] = None