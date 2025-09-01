import json
import os
from typing import Dict, Any, Optional, Type, List
from dataclasses import dataclass
import importlib
import logging
from pathlib import Path

from providers.base_providers import (
    PriceDataProvider, ExecutionProvider, NewsProvider, AnalyticsProvider
)

logger = logging.getLogger(__name__)

@dataclass
class ProviderConfig:
    """Configuration for a specific provider"""
    provider_type: str  # price_data, execution, news, analytics
    provider_name: str  # polygon_io, tradestation, etc.
    class_name: str
    module_path: str
    config: Dict[str, Any]
    credentials: Dict[str, Any]

class DIContainer:
    """Dependency Injection Container for provider management"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self._providers: Dict[str, Any] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
        
        # Load configurations
        self._load_configurations()
        
    def _load_configurations(self):
        """Load all configuration files"""
        try:
            # Load provider configuration
            with open(self.config_dir / "providers_config.json", 'r') as f:
                self.providers_config = json.load(f)
                
            # Load API credentials
            with open(self.config_dir / "api_credentials.json", 'r') as f:
                self.credentials_config = json.load(f)
                
            # Load modes configuration
            with open(self.config_dir / "modes_config.json", 'r') as f:
                self.modes_config = json.load(f)
                
            logger.info("Configuration files loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration files: {e}")
            raise
    
    def _substitute_env_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration"""
        def substitute_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(v) for v in value]
            return value
            
        return substitute_value(config)
    
    def _get_provider_class_mapping(self) -> Dict[str, Dict[str, str]]:
        """Map provider names to their implementation classes"""
        return {
            "price_data": {
                "polygon_io": {
                    "module": "providers.polygon_price_provider",
                    "class": "PolygonPriceProvider"
                },
                "yahoo_finance": {
                    "module": "providers.yahoo_price_provider", 
                    "class": "YahooFinanceProvider"
                },
                "alpha_vantage": {
                    "module": "providers.alpha_vantage_provider",
                    "class": "AlphaVantageProvider"
                }
            },
            "execution": {
                "tradestation": {
                    "module": "providers.tradestation_executor",
                    "class": "TradeStationExecutor"
                },
                "defi": {
                    "module": "providers.defi_executor",
                    "class": "DeFiExecutor"
                },
                "auto_route": {
                    "module": "providers.auto_router",
                    "class": "AutoRouter"
                }
            },
            "news": {
                "polygon_news": {
                    "module": "providers.polygon_news_provider",
                    "class": "PolygonNewsProvider"  
                },
                "alpha_vantage_news": {
                    "module": "providers.alpha_vantage_news_provider",
                    "class": "AlphaVantageNewsProvider"
                }
            },
            "analytics": {
                "internal_ta": {
                    "module": "providers.internal_analytics_provider",
                    "class": "InternalAnalyticsProvider"
                }
            }
        }
    
    def _create_provider(self, provider_type: str, provider_name: str) -> Any:
        """Create a provider instance"""
        try:
            # Get class mapping
            class_mapping = self._get_provider_class_mapping()
            
            if provider_type not in class_mapping:
                raise ValueError(f"Unknown provider type: {provider_type}")
                
            if provider_name not in class_mapping[provider_type]:
                raise ValueError(f"Unknown provider '{provider_name}' for type '{provider_type}'")
            
            # Get module and class info
            provider_info = class_mapping[provider_type][provider_name]
            module_name = provider_info["module"]
            class_name = provider_info["class"]
            
            # Import module and get class
            module = importlib.import_module(module_name)
            provider_class = getattr(module, class_name)
            
            # Get configuration and credentials
            provider_config = self.providers_config.get("provider_settings", {}).get(provider_name, {})
            provider_credentials = self.credentials_config.get(provider_name, {})
            
            # Substitute environment variables
            provider_credentials = self._substitute_env_variables(provider_credentials)
            
            # Create provider instance
            provider_instance = provider_class(
                config=provider_config,
                credentials=provider_credentials
            )
            
            logger.info(f"Created provider: {provider_type}/{provider_name}")
            return provider_instance
            
        except Exception as e:
            logger.error(f"Error creating provider {provider_type}/{provider_name}: {e}")
            raise
    
    def get_price_provider(self) -> PriceDataProvider:
        """Get the configured price data provider"""
        current_mode = self.modes_config["current_mode"]
        mode_config = self.modes_config["trading_modes"][current_mode]
        provider_name = mode_config["providers"]["price_data"]
        
        cache_key = f"price_data_{provider_name}"
        if cache_key not in self._providers:
            self._providers[cache_key] = self._create_provider("price_data", provider_name)
            
        return self._providers[cache_key]
    
    def get_execution_provider(self) -> ExecutionProvider:
        """Get the configured execution provider"""
        current_mode = self.modes_config["current_mode"] 
        mode_config = self.modes_config["trading_modes"][current_mode]
        provider_name = mode_config["providers"]["execution"]
        
        cache_key = f"execution_{provider_name}"
        if cache_key not in self._providers:
            self._providers[cache_key] = self._create_provider("execution", provider_name)
            
        return self._providers[cache_key]
    
    def get_news_provider(self) -> Optional[NewsProvider]:
        """Get the configured news provider"""
        try:
            current_mode = self.modes_config["current_mode"]
            mode_config = self.modes_config["trading_modes"][current_mode]
            provider_name = mode_config["providers"]["news"]
            
            cache_key = f"news_{provider_name}"
            if cache_key not in self._providers:
                self._providers[cache_key] = self._create_provider("news", provider_name)
                
            return self._providers[cache_key]
        except Exception as e:
            logger.warning(f"News provider not available: {e}")
            return None
    
    def get_analytics_provider(self) -> Optional[AnalyticsProvider]:
        """Get the configured analytics provider"""
        try:
            current_mode = self.modes_config["current_mode"]
            mode_config = self.modes_config["trading_modes"][current_mode]
            provider_name = mode_config["providers"]["analytics"]
            
            cache_key = f"analytics_{provider_name}"
            if cache_key not in self._providers:
                self._providers[cache_key] = self._create_provider("analytics", provider_name)
                
            return self._providers[cache_key]
        except Exception as e:
            logger.warning(f"Analytics provider not available: {e}")
            return None
    
    def get_fallback_price_provider(self) -> Optional[PriceDataProvider]:
        """Get fallback price provider if primary fails"""
        fallback_providers = self.providers_config.get("fallback_providers", {}).get("price_data", [])
        
        for provider_name in fallback_providers:
            try:
                cache_key = f"price_data_{provider_name}_fallback"
                if cache_key not in self._providers:
                    self._providers[cache_key] = self._create_provider("price_data", provider_name)
                return self._providers[cache_key]
            except Exception as e:
                logger.warning(f"Fallback provider {provider_name} failed: {e}")
                continue
        
        return None
    
    def get_current_mode_config(self) -> Dict[str, Any]:
        """Get current trading mode configuration"""
        current_mode = self.modes_config["current_mode"]
        return self.modes_config["trading_modes"][current_mode]
    
    def switch_mode(self, new_mode: str):
        """Switch trading mode"""
        if new_mode not in self.modes_config["trading_modes"]:
            raise ValueError(f"Unknown trading mode: {new_mode}")
            
        logger.info(f"Switching from {self.modes_config['current_mode']} to {new_mode}")
        self.modes_config["current_mode"] = new_mode
        
        # Clear provider cache to force recreation with new mode
        self._providers.clear()
    
    def health_check_all_providers(self) -> Dict[str, Any]:
        """Perform health check on all active providers"""
        results = {}
        
        try:
            # Check price provider
            price_provider = self.get_price_provider()
            results["price_data"] = price_provider.health_check()
        except Exception as e:
            results["price_data"] = f"Error: {e}"
            
        try:
            # Check execution provider  
            execution_provider = self.get_execution_provider()
            results["execution"] = execution_provider.health_check()
        except Exception as e:
            results["execution"] = f"Error: {e}"
            
        try:
            # Check news provider
            news_provider = self.get_news_provider()
            if news_provider:
                results["news"] = news_provider.health_check()
        except Exception as e:
            results["news"] = f"Error: {e}"
            
        try:
            # Check analytics provider
            analytics_provider = self.get_analytics_provider()
            if analytics_provider:
                results["analytics"] = analytics_provider.health_check()
        except Exception as e:
            results["analytics"] = f"Error: {e}"
            
        return results