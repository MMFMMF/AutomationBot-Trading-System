"""
Centralized Configuration Management System for AutomationBot Trading Platform

This module provides unified configuration management, validation, and 
persistence across all system components.
"""

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from core.api_response import APIException, ErrorCode, validate_strategy


@dataclass
class TradingConfig:
    """Trading system configuration"""
    capital_amount: float = 50000.0
    max_positions: int = 5
    risk_per_trade: float = 0.02
    strategies_enabled: List[str] = None
    signal_interval: int = 30
    auto_trading: bool = False
    
    def __post_init__(self):
        if self.strategies_enabled is None:
            self.strategies_enabled = ['mixed']


@dataclass
class ProviderConfig:
    """Provider configuration settings"""
    price_data_provider: str = "polygon"
    execution_provider: str = "paper"
    news_provider: str = "polygon"
    analytics_provider: str = "internal"
    provider_overrides: Dict[str, str] = None
    
    def __post_init__(self):
        if self.provider_overrides is None:
            self.provider_overrides = {}


@dataclass
class SystemConfig:
    """System-wide configuration settings"""
    debug_mode: bool = False
    logging_level: str = "INFO"
    database_path: str = "./data/automation_bot.db"
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds
    api_rate_limit: int = 100
    web_interface_enabled: bool = True
    
    
@dataclass
class SecurityConfig:
    """Security and authentication configuration"""
    api_keys_encrypted: bool = True
    session_timeout: int = 3600
    max_login_attempts: int = 3
    require_2fa: bool = False
    allowed_origins: List[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ['localhost', '127.0.0.1']


class ConfigurationManager:
    """
    Centralized configuration management with validation, persistence, and change notifications
    """
    
    def __init__(self, config_file: str = "config/platform_config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Configuration sections
        self.trading = TradingConfig()
        self.providers = ProviderConfig()
        self.system = SystemConfig()
        self.security = SecurityConfig()
        
        # Thread safety
        self._lock = threading.RLock()
        self._change_callbacks = {}
        
        # Load existing configuration
        self._load_config()
    
    def get_trading_config(self) -> TradingConfig:
        """Get current trading configuration"""
        with self._lock:
            return self.trading
    
    def update_trading_config(self, **kwargs) -> Dict[str, Any]:
        """
        Update trading configuration with validation
        
        Args:
            **kwargs: Configuration fields to update
            
        Returns:
            Updated configuration as dict
            
        Raises:
            APIException: If validation fails
        """
        with self._lock:
            # Validate updates
            if 'capital_amount' in kwargs:
                amount = kwargs['capital_amount']
                if not isinstance(amount, (int, float)) or amount <= 0:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "Capital amount must be a positive number"
                    )
                if amount < 1000:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "Capital amount must be at least $1,000"
                    )
            
            if 'max_positions' in kwargs:
                positions = kwargs['max_positions']
                if not isinstance(positions, int) or positions <= 0 or positions > 50:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "Max positions must be between 1 and 50"
                    )
            
            if 'risk_per_trade' in kwargs:
                risk = kwargs['risk_per_trade']
                if not isinstance(risk, (int, float)) or risk <= 0 or risk > 0.1:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "Risk per trade must be between 0.001 and 0.1 (0.1% to 10%)"
                    )
            
            if 'strategies_enabled' in kwargs:
                strategies = kwargs['strategies_enabled']
                if not isinstance(strategies, list) or not strategies:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "At least one strategy must be enabled"
                    )
                for strategy in strategies:
                    validate_strategy(strategy)
            
            # Apply updates
            old_config = asdict(self.trading)
            for key, value in kwargs.items():
                if hasattr(self.trading, key):
                    setattr(self.trading, key, value)
            
            # Save configuration
            self._save_config()
            
            # Notify listeners
            self._notify_changes('trading', old_config, asdict(self.trading))
            
            return asdict(self.trading)
    
    def get_provider_config(self) -> ProviderConfig:
        """Get current provider configuration"""
        with self._lock:
            return self.providers
    
    def update_provider_config(self, **kwargs) -> Dict[str, Any]:
        """
        Update provider configuration with validation
        
        Args:
            **kwargs: Configuration fields to update
            
        Returns:
            Updated configuration as dict
        """
        with self._lock:
            valid_providers = {
                'price_data': ['polygon', 'alpha_vantage', 'yahoo', 'mock'],
                'execution': ['paper', 'alpaca', 'mock'],
                'news': ['polygon', 'alpha_vantage', 'mock'],
                'analytics': ['internal', 'mock']
            }
            
            # Validate provider selections
            for field, value in kwargs.items():
                if field.endswith('_provider'):
                    provider_type = field.replace('_provider', '')
                    if provider_type in valid_providers:
                        if value not in valid_providers[provider_type]:
                            raise APIException(
                                ErrorCode.INVALID_PARAMETER,
                                f"Invalid {provider_type} provider: {value}",
                                f"Valid options: {', '.join(valid_providers[provider_type])}"
                            )
            
            # Apply updates
            old_config = asdict(self.providers)
            for key, value in kwargs.items():
                if hasattr(self.providers, key):
                    setattr(self.providers, key, value)
            
            # Save configuration
            self._save_config()
            
            # Notify listeners
            self._notify_changes('providers', old_config, asdict(self.providers))
            
            return asdict(self.providers)
    
    def get_system_config(self) -> SystemConfig:
        """Get current system configuration"""
        with self._lock:
            return self.system
    
    def update_system_config(self, **kwargs) -> Dict[str, Any]:
        """
        Update system configuration with validation
        
        Args:
            **kwargs: Configuration fields to update
            
        Returns:
            Updated configuration as dict
        """
        with self._lock:
            # Validate system config updates
            if 'logging_level' in kwargs:
                level = kwargs['logging_level']
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if level not in valid_levels:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        f"Invalid logging level: {level}",
                        f"Valid levels: {', '.join(valid_levels)}"
                    )
            
            if 'api_rate_limit' in kwargs:
                limit = kwargs['api_rate_limit']
                if not isinstance(limit, int) or limit <= 0 or limit > 10000:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        "API rate limit must be between 1 and 10000"
                    )
            
            # Apply updates
            old_config = asdict(self.system)
            for key, value in kwargs.items():
                if hasattr(self.system, key):
                    setattr(self.system, key, value)
            
            # Save configuration
            self._save_config()
            
            # Notify listeners
            self._notify_changes('system', old_config, asdict(self.system))
            
            return asdict(self.system)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete system configuration"""
        with self._lock:
            return {
                'trading': asdict(self.trading),
                'providers': asdict(self.providers),
                'system': asdict(self.system),
                'security': asdict(self.security),
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'config_file': str(self.config_file),
                    'version': '2.1'
                }
            }
    
    def reset_to_defaults(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset configuration to defaults
        
        Args:
            section: Specific section to reset, or None for all sections
            
        Returns:
            Reset configuration
        """
        with self._lock:
            if section == 'trading' or section is None:
                self.trading = TradingConfig()
            if section == 'providers' or section is None:
                self.providers = ProviderConfig()
            if section == 'system' or section is None:
                self.system = SystemConfig()
            if section == 'security' or section is None:
                self.security = SecurityConfig()
            
            self._save_config()
            return self.get_all_config()
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate current configuration and return validation results
        
        Returns:
            Validation results with any issues found
        """
        issues = []
        warnings = []
        
        # Validate trading config
        if self.trading.capital_amount < 10000:
            warnings.append("Capital amount below recommended minimum of $10,000")
        
        if self.trading.risk_per_trade > 0.05:
            warnings.append("Risk per trade above recommended maximum of 5%")
        
        if not self.trading.strategies_enabled:
            issues.append("No trading strategies enabled")
        
        # Validate provider config
        required_providers = ['price_data_provider', 'execution_provider']
        for provider in required_providers:
            if not getattr(self.providers, provider):
                issues.append(f"Required provider not configured: {provider}")
        
        # Validate system config
        if self.system.debug_mode and not self.system.logging_level == 'DEBUG':
            warnings.append("Debug mode enabled but logging level not set to DEBUG")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'validation_timestamp': datetime.now().isoformat()
        }
    
    def register_change_callback(self, section: str, callback):
        """
        Register callback for configuration changes
        
        Args:
            section: Configuration section to monitor
            callback: Function to call on changes
        """
        if section not in self._change_callbacks:
            self._change_callbacks[section] = []
        self._change_callbacks[section].append(callback)
    
    def _load_config(self):
        """Load configuration from file"""
        if not self.config_file.exists():
            self._save_config()  # Create with defaults
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Load each section
            if 'trading' in config_data:
                self.trading = TradingConfig(**config_data['trading'])
            if 'providers' in config_data:
                self.providers = ProviderConfig(**config_data['providers'])
            if 'system' in config_data:
                self.system = SystemConfig(**config_data['system'])
            if 'security' in config_data:
                self.security = SecurityConfig(**config_data['security'])
                
        except Exception as e:
            # If loading fails, use defaults and save
            print(f"Warning: Could not load config file: {e}. Using defaults.")
            self._save_config()
    
    def _save_config(self):
        """Save current configuration to file"""
        try:
            config_data = {
                'trading': asdict(self.trading),
                'providers': asdict(self.providers),
                'system': asdict(self.system),
                'security': asdict(self.security),
                'metadata': {
                    'last_saved': datetime.now().isoformat(),
                    'version': '2.1'
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def _notify_changes(self, section: str, old_config: Dict, new_config: Dict):
        """Notify registered callbacks of configuration changes"""
        if section in self._change_callbacks:
            changes = {k: new_config[k] for k in new_config if new_config[k] != old_config.get(k)}
            if changes:
                for callback in self._change_callbacks[section]:
                    try:
                        callback(section, old_config, new_config, changes)
                    except Exception as e:
                        print(f"Error in config change callback: {e}")


# Global configuration manager instance
config_manager = ConfigurationManager()


# Validation utilities for common configuration patterns
def validate_capital_allocation(allocations: Dict[str, float]) -> None:
    """
    Validate capital allocation percentages
    
    Args:
        allocations: Dictionary of allocation percentages
        
    Raises:
        APIException: If validation fails
    """
    if not isinstance(allocations, dict):
        raise APIException(
            ErrorCode.INVALID_PARAMETER,
            "Allocations must be a dictionary"
        )
    
    total = sum(allocations.values())
    if not (0.95 <= total <= 1.05):  # Allow small rounding differences
        raise APIException(
            ErrorCode.INVALID_PARAMETER,
            f"Allocation percentages must sum to 100%, got {total * 100:.1f}%"
        )
    
    for category, percentage in allocations.items():
        if not isinstance(percentage, (int, float)) or percentage < 0 or percentage > 1:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                f"Invalid allocation for {category}: {percentage}. Must be between 0 and 1."
            )


def validate_risk_parameters(max_drawdown: float = None, var_threshold: float = None) -> None:
    """
    Validate risk management parameters
    
    Args:
        max_drawdown: Maximum allowed drawdown percentage
        var_threshold: Value at Risk threshold
        
    Raises:
        APIException: If validation fails
    """
    if max_drawdown is not None:
        if not isinstance(max_drawdown, (int, float)) or max_drawdown <= 0 or max_drawdown > 0.5:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Max drawdown must be between 0.1% and 50%"
            )
    
    if var_threshold is not None:
        if not isinstance(var_threshold, (int, float)) or var_threshold <= 0:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "VaR threshold must be a positive number"
            )