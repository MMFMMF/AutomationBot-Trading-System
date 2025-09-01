import os
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TradingConfig:
    """Core trading configuration"""
    capital: float = float(os.getenv('TRADING_CAPITAL', 16000))
    operating_mode: Literal['tradestation_only', 'hybrid', 'defi_only'] = os.getenv('OPERATING_MODE', 'tradestation_only')
    max_position_size_pct: float = float(os.getenv('MAX_POSITION_SIZE_PCT', 0.10))
    max_daily_loss_pct: float = float(os.getenv('MAX_DAILY_LOSS_PCT', 0.05))
    min_account_balance: float = float(os.getenv('MIN_ACCOUNT_BALANCE', 14000))

@dataclass
class APIConfig:
    """API configuration for external services"""
    polygon_api_key: str = os.getenv('POLYGON_API_KEY', '')
    tradestation_client_id: str = os.getenv('TRADESTATION_CLIENT_ID', '')
    tradestation_client_secret: str = os.getenv('TRADESTATION_CLIENT_SECRET', '')

@dataclass
class SystemConfig:
    """System-level configuration"""
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    database_path: str = os.getenv('DATABASE_PATH', './data/automation_bot.db')
    api_port: int = int(os.getenv('API_PORT', 5000))

# Global configuration instances
trading_config = TradingConfig()
api_config = APIConfig()
system_config = SystemConfig()

# Execution venue mapping based on operating mode
EXECUTION_VENUES = {
    'tradestation_only': ['tradestation'],
    'hybrid': ['tradestation', 'defi'],
    'defi_only': ['defi']
}

# Block reason codes
BLOCK_REASONS = {
    'INSUFFICIENT_CAPITAL': 'Insufficient capital for position',
    'MAX_POSITION_EXCEEDED': 'Position size exceeds maximum allowed',
    'DAILY_LOSS_LIMIT': 'Daily loss limit reached',
    'MARKET_CLOSED': 'Market is closed for trading',
    'INVALID_SYMBOL': 'Symbol not tradeable',
    'API_ERROR': 'API connection error',
    'RISK_LIMIT_EXCEEDED': 'Trade exceeds risk parameters',
    'VENUE_UNAVAILABLE': 'Trading venue unavailable'
}