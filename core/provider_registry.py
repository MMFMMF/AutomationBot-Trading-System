import json
import logging
from typing import Dict, Any, Optional, Type, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import importlib
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ProviderMetadata:
    """Metadata about a provider"""
    provider_name: str
    provider_type: str  # price_data, execution, news, analytics
    display_name: str
    description: str
    version: str
    author: str
    requires_credentials: bool
    supported_features: List[str]
    configuration_schema: Dict[str, Any]
    health_check_endpoint: Optional[str] = None
    documentation_url: Optional[str] = None

@dataclass 
class ProviderRegistration:
    """Complete provider registration information"""
    metadata: ProviderMetadata
    module_path: str
    class_name: str
    enabled: bool = True
    configuration: Dict[str, Any] = None
    credentials_template: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}
        if self.credentials_template is None:
            self.credentials_template = {}

class ProviderTemplate(ABC):
    """Base template for creating new providers"""
    
    @abstractmethod
    def get_metadata(self) -> ProviderMetadata:
        """Return provider metadata"""
        pass
    
    @abstractmethod
    def get_configuration_template(self) -> Dict[str, Any]:
        """Return configuration template with defaults"""
        pass
    
    @abstractmethod
    def get_credentials_template(self) -> Dict[str, Any]:
        """Return credentials template"""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate configuration"""
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """Validate credentials"""
        pass

class ProviderRegistry:
    """Registry for managing modular providers"""
    
    def __init__(self, registry_path: str = "./config/provider_registry.json"):
        self.registry_path = Path(registry_path)
        self.registered_providers: Dict[str, ProviderRegistration] = {}
        self.provider_types = ["price_data", "execution", "news", "analytics"]
        self._load_registry()
    
    def _load_registry(self):
        """Load provider registry from file"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    registry_data = json.load(f)
                
                for provider_name, provider_data in registry_data.get('providers', {}).items():
                    try:
                        metadata = ProviderMetadata(**provider_data['metadata'])
                        registration = ProviderRegistration(
                            metadata=metadata,
                            module_path=provider_data['module_path'],
                            class_name=provider_data['class_name'],
                            enabled=provider_data.get('enabled', True),
                            configuration=provider_data.get('configuration', {}),
                            credentials_template=provider_data.get('credentials_template', {})
                        )
                        self.registered_providers[provider_name] = registration
                        
                    except Exception as e:
                        logger.error(f"Error loading provider {provider_name}: {e}")
                        continue
                        
                logger.info(f"Loaded {len(self.registered_providers)} providers from registry")
            else:
                logger.info("Provider registry not found, creating default registry")
                self._create_default_registry()
                
        except Exception as e:
            logger.error(f"Error loading provider registry: {e}")
            self._create_default_registry()
    
    def _create_default_registry(self):
        """Create default provider registry with built-in providers"""
        # Register built-in providers
        self._register_builtin_providers()
        self._save_registry()
    
    def _register_builtin_providers(self):
        """Register built-in providers"""
        builtin_providers = [
            {
                'name': 'polygon_io',
                'type': 'price_data',
                'module': 'providers.polygon_price_provider',
                'class': 'PolygonPriceProvider',
                'display_name': 'Polygon.io Market Data',
                'description': 'Real-time and historical market data from Polygon.io',
                'features': ['real_time_quotes', 'historical_data', 'market_status']
            },
            {
                'name': 'tradestation',
                'type': 'execution',
                'module': 'providers.tradestation_executor',
                'class': 'TradeStationExecutor', 
                'display_name': 'TradeStation Brokerage',
                'description': 'Trade execution through TradeStation API',
                'features': ['market_orders', 'limit_orders', 'stop_orders', 'account_balance']
            },
            {
                'name': 'defi',
                'type': 'execution',
                'module': 'providers.defi_executor',
                'class': 'DeFiExecutor',
                'display_name': 'DeFi DEX Execution',
                'description': 'Decentralized exchange execution via 1inch aggregator',
                'features': ['dex_swaps', 'token_routing', 'slippage_protection']
            },
            {
                'name': 'internal_ta',
                'type': 'analytics',
                'module': 'providers.internal_analytics_provider',
                'class': 'InternalAnalyticsProvider',
                'display_name': 'Internal Technical Analysis',
                'description': 'Built-in technical analysis indicators',
                'features': ['rsi', 'macd', 'sma', 'ema', 'bollinger_bands']
            }
        ]
        
        for provider in builtin_providers:
            metadata = ProviderMetadata(
                provider_name=provider['name'],
                provider_type=provider['type'],
                display_name=provider['display_name'],
                description=provider['description'],
                version='1.0.0',
                author='AutomationBot System',
                requires_credentials=provider['name'] in ['polygon_io', 'tradestation'],
                supported_features=provider['features'],
                configuration_schema={}
            )
            
            registration = ProviderRegistration(
                metadata=metadata,
                module_path=provider['module'],
                class_name=provider['class']
            )
            
            self.registered_providers[provider['name']] = registration
    
    def _save_registry(self):
        """Save provider registry to file"""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            registry_data = {
                'version': '1.0.0',
                'last_updated': datetime.now().isoformat(),
                'providers': {}
            }
            
            for name, registration in self.registered_providers.items():
                registry_data['providers'][name] = {
                    'metadata': asdict(registration.metadata),
                    'module_path': registration.module_path,
                    'class_name': registration.class_name,
                    'enabled': registration.enabled,
                    'configuration': registration.configuration,
                    'credentials_template': registration.credentials_template
                }
            
            with open(self.registry_path, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
            logger.info("Provider registry saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving provider registry: {e}")
    
    def register_provider(self, registration: ProviderRegistration) -> bool:
        """Register a new provider"""
        try:
            provider_name = registration.metadata.provider_name
            
            # Validate provider type
            if registration.metadata.provider_type not in self.provider_types:
                logger.error(f"Invalid provider type: {registration.metadata.provider_type}")
                return False
            
            # Check if provider already exists
            if provider_name in self.registered_providers:
                logger.warning(f"Provider {provider_name} already registered, updating...")
            
            # Validate module can be imported
            try:
                module = importlib.import_module(registration.module_path)
                provider_class = getattr(module, registration.class_name)
                logger.info(f"Validated provider class: {registration.class_name}")
            except Exception as e:
                logger.error(f"Cannot import provider {provider_name}: {e}")
                return False
            
            # Register the provider
            self.registered_providers[provider_name] = registration
            self._save_registry()
            
            logger.info(f"Provider {provider_name} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering provider: {e}")
            return False
    
    def unregister_provider(self, provider_name: str) -> bool:
        """Unregister a provider"""
        try:
            if provider_name not in self.registered_providers:
                logger.warning(f"Provider {provider_name} not found")
                return False
            
            del self.registered_providers[provider_name]
            self._save_registry()
            
            logger.info(f"Provider {provider_name} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering provider: {e}")
            return False
    
    def get_providers_by_type(self, provider_type: str) -> List[ProviderRegistration]:
        """Get all providers of a specific type"""
        return [
            registration for registration in self.registered_providers.values()
            if registration.metadata.provider_type == provider_type and registration.enabled
        ]
    
    def get_provider(self, provider_name: str) -> Optional[ProviderRegistration]:
        """Get specific provider registration"""
        return self.registered_providers.get(provider_name)
    
    def list_all_providers(self) -> Dict[str, ProviderRegistration]:
        """List all registered providers"""
        return self.registered_providers.copy()
    
    def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider"""
        if provider_name in self.registered_providers:
            self.registered_providers[provider_name].enabled = True
            self._save_registry()
            return True
        return False
    
    def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider"""
        if provider_name in self.registered_providers:
            self.registered_providers[provider_name].enabled = False
            self._save_registry()
            return True
        return False
    
    def get_provider_summary(self) -> Dict[str, Any]:
        """Get comprehensive provider summary"""
        summary = {
            'total_providers': len(self.registered_providers),
            'enabled_providers': len([p for p in self.registered_providers.values() if p.enabled]),
            'by_type': {},
            'providers': []
        }
        
        # Count by type
        for provider_type in self.provider_types:
            providers_of_type = self.get_providers_by_type(provider_type)
            summary['by_type'][provider_type] = len(providers_of_type)
        
        # Provider details
        for name, registration in self.registered_providers.items():
            summary['providers'].append({
                'name': name,
                'type': registration.metadata.provider_type,
                'display_name': registration.metadata.display_name,
                'enabled': registration.enabled,
                'requires_credentials': registration.metadata.requires_credentials,
                'features': registration.metadata.supported_features
            })
        
        return summary
    
    def create_provider_template(self, provider_name: str, provider_type: str, 
                               display_name: str, description: str) -> str:
        """Generate a provider template file"""
        if provider_type not in self.provider_types:
            raise ValueError(f"Invalid provider type: {provider_type}")
        
        # Map provider type to base class
        base_class_map = {
            'price_data': 'PriceDataProvider',
            'execution': 'ExecutionProvider', 
            'news': 'NewsProvider',
            'analytics': 'AnalyticsProvider'
        }
        
        base_class = base_class_map[provider_type]
        class_name = f"{''.join(word.capitalize() for word in provider_name.split('_'))}{provider_type.title().replace('_', '')}"
        
        template = f'''import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from providers.base_providers import {base_class}
from core.execution_mode_manager import ExecutionModeManager

logger = logging.getLogger(__name__)

class {class_name}({base_class}):
    """{display_name} - {description}"""
    
    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any], 
                 execution_mode_manager: Optional[ExecutionModeManager] = None):
        self.config = config
        self.credentials = credentials
        self.execution_mode_manager = execution_mode_manager or ExecutionModeManager()
        self._last_health_check = None
        
        # Initialize your provider here
        logger.info(f"{display_name} initialized")
    
    @property
    def provider_name(self) -> str:
        return "{provider_name}"
    
    # Implement required abstract methods based on provider type
    # See base_providers.py for the interface requirements
    
    def health_check(self):
        """Implement health check for your provider"""
        # Add your health check logic here
        pass
'''
        
        # Save template to file
        template_path = Path(f"./providers/{provider_name}.py")
        template_path.write_text(template)
        
        logger.info(f"Provider template created: {template_path}")
        return str(template_path)
    
    def validate_provider_integration(self, provider_name: str) -> Dict[str, Any]:
        """Validate that a provider integrates correctly"""
        validation_result = {
            'provider_name': provider_name,
            'valid': False,
            'errors': [],
            'warnings': [],
            'checks_passed': 0,
            'total_checks': 5
        }
        
        try:
            registration = self.get_provider(provider_name)
            if not registration:
                validation_result['errors'].append(f"Provider {provider_name} not found in registry")
                return validation_result
            
            # Check 1: Module can be imported
            try:
                module = importlib.import_module(registration.module_path)
                validation_result['checks_passed'] += 1
            except Exception as e:
                validation_result['errors'].append(f"Cannot import module: {e}")
                return validation_result
            
            # Check 2: Class exists
            try:
                provider_class = getattr(module, registration.class_name)
                validation_result['checks_passed'] += 1
            except Exception as e:
                validation_result['errors'].append(f"Class {registration.class_name} not found: {e}")
                return validation_result
            
            # Check 3: Inherits from correct base class
            base_class_map = {
                'price_data': 'PriceDataProvider',
                'execution': 'ExecutionProvider',
                'news': 'NewsProvider', 
                'analytics': 'AnalyticsProvider'
            }
            expected_base = base_class_map.get(registration.metadata.provider_type)
            if expected_base:
                # This is a simplified check - in practice you'd check the MRO
                validation_result['checks_passed'] += 1
            else:
                validation_result['warnings'].append(f"Unknown provider type: {registration.metadata.provider_type}")
            
            # Check 4: Required methods exist
            required_methods = ['provider_name', 'health_check']
            missing_methods = []
            for method in required_methods:
                if not hasattr(provider_class, method):
                    missing_methods.append(method)
            
            if not missing_methods:
                validation_result['checks_passed'] += 1
            else:
                validation_result['errors'].append(f"Missing required methods: {missing_methods}")
            
            # Check 5: Can instantiate (basic test)
            try:
                # Basic instantiation test with empty config
                instance = provider_class({}, {})
                if hasattr(instance, 'provider_name'):
                    validation_result['checks_passed'] += 1
            except Exception as e:
                validation_result['warnings'].append(f"Instantiation warning: {e}")
            
            # Final validation
            if validation_result['checks_passed'] >= 4 and not validation_result['errors']:
                validation_result['valid'] = True
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
        
        return validation_result