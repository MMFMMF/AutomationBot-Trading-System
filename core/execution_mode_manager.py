import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import time
import random

logger = logging.getLogger(__name__)

class ExecutionModeManager:
    """Manages execution vs simulation mode across all providers"""
    
    def __init__(self, config_path: str = "./config/execution_config.json"):
        self.config_path = Path(config_path)
        self.execution_config = {}
        self._load_execution_config()
    
    def _load_execution_config(self):
        """Load execution configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.execution_config = json.load(f)
                logger.info(f"Execution configuration loaded. Mode: {'EXECUTION' if self.is_execution_mode() else 'SIMULATION'}")
            else:
                logger.warning("Execution configuration file not found. Creating default.")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading execution configuration: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default execution configuration"""
        self.execution_config = {
            "execution_mode": False,  # Start in simulation mode for safety
            "simulation_settings": {
                "realistic_delays": True,
                "simulate_api_failures": False,
                "log_all_actions": True,
                "failure_rate": 0.05
            },
            "execution_settings": {
                "confirm_trades": True,
                "dry_run_first": True,
                "max_trade_value": 10000
            },
            "provider_overrides": {},
            "last_updated": None
        }
        self._save_execution_config()
    
    def _save_execution_config(self):
        """Save execution configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.execution_config['last_updated'] = datetime.now().isoformat()
            with open(self.config_path, 'w') as f:
                json.dump(self.execution_config, f, indent=2)
            logger.info("Execution configuration saved")
        except Exception as e:
            logger.error(f"Error saving execution configuration: {e}")
    
    def is_execution_mode(self) -> bool:
        """Check if system is in execution mode"""
        return self.execution_config.get('execution_mode', False)
    
    def is_simulation_mode(self) -> bool:
        """Check if system is in simulation mode"""
        return not self.is_execution_mode()
    
    def set_execution_mode(self, enabled: bool) -> bool:
        """Set execution mode on/off"""
        try:
            old_mode = self.is_execution_mode()
            self.execution_config['execution_mode'] = enabled
            self._save_execution_config()
            
            new_mode = "EXECUTION" if enabled else "SIMULATION"
            old_mode_str = "EXECUTION" if old_mode else "SIMULATION"
            logger.warning(f"Mode switched: {old_mode_str} -> {new_mode}")
            return True
        except Exception as e:
            logger.error(f"Error setting execution mode: {e}")
            return False
    
    def get_provider_mode(self, provider_name: str) -> tuple[bool, str]:
        """Get execution mode for specific provider (considering overrides)"""
        provider_overrides = self.execution_config.get('provider_overrides', {})
        
        if provider_name in provider_overrides:
            override = provider_overrides[provider_name]
            if override.get('force_simulation', False):
                return False, override.get('reason', 'Provider override')
        
        return self.is_execution_mode(), "Global setting"
    
    def simulate_api_delay(self, operation: str = "api_call"):
        """Add realistic delay for simulation mode"""
        if self.is_simulation_mode() and self.execution_config['simulation_settings'].get('realistic_delays', True):
            # Simulate realistic API response times
            delay_ranges = {
                'api_call': (0.1, 0.5),
                'order_execution': (0.2, 1.0),
                'balance_check': (0.1, 0.3),
                'price_fetch': (0.05, 0.2)
            }
            
            min_delay, max_delay = delay_ranges.get(operation, (0.1, 0.5))
            delay = random.uniform(min_delay, max_delay)
            time.sleep(delay)
    
    def should_simulate_failure(self) -> bool:
        """Determine if API call should simulate a failure"""
        if self.is_simulation_mode() and self.execution_config['simulation_settings'].get('simulate_api_failures', False):
            failure_rate = self.execution_config['simulation_settings'].get('failure_rate', 0.05)
            return random.random() < failure_rate
        return False
    
    def log_action(self, provider: str, action: str, details: Dict[str, Any]):
        """Log provider actions for audit trail"""
        if self.execution_config['simulation_settings'].get('log_all_actions', True):
            mode = "EXECUTION" if self.is_execution_mode() else "SIMULATION"
            logger.info(f"[{mode}] {provider}: {action} - {details}")
    
    def validate_execution_safety(self, provider: str, action: str, value: float = 0) -> tuple[bool, str]:
        """Validate if execution is safe to proceed"""
        if self.is_simulation_mode():
            return True, "Simulation mode - safe to proceed"
        
        # Check provider-specific overrides
        is_allowed, reason = self.get_provider_mode(provider)
        if not is_allowed:
            return False, f"Provider {provider} forced to simulation: {reason}"
        
        # Check execution settings
        execution_settings = self.execution_config.get('execution_settings', {})
        max_trade_value = execution_settings.get('max_trade_value', 10000)
        
        if value > max_trade_value:
            return False, f"Trade value ${value:,.2f} exceeds maximum ${max_trade_value:,.2f}"
        
        return True, "Execution validated"
    
    def get_mode_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution mode summary"""
        provider_modes = {}
        providers = ['tradestation', 'defi', 'polygon_io', 'internal_ta']
        
        for provider in providers:
            is_execution, reason = self.get_provider_mode(provider)
            provider_modes[provider] = {
                'execution_mode': is_execution,
                'mode_string': 'EXECUTION' if is_execution else 'SIMULATION',
                'reason': reason
            }
        
        return {
            'global_execution_mode': self.is_execution_mode(),
            'global_mode_string': 'EXECUTION' if self.is_execution_mode() else 'SIMULATION',
            'provider_modes': provider_modes,
            'simulation_settings': self.execution_config.get('simulation_settings', {}),
            'execution_settings': self.execution_config.get('execution_settings', {}),
            'last_updated': self.execution_config.get('last_updated')
        }
    
    def set_provider_override(self, provider: str, force_simulation: bool, reason: str = "") -> bool:
        """Set provider-specific execution override"""
        try:
            if 'provider_overrides' not in self.execution_config:
                self.execution_config['provider_overrides'] = {}
            
            if force_simulation:
                self.execution_config['provider_overrides'][provider] = {
                    'force_simulation': True,
                    'reason': reason or f'{provider} forced to simulation'
                }
            else:
                # Remove override
                if provider in self.execution_config['provider_overrides']:
                    del self.execution_config['provider_overrides'][provider]
            
            self._save_execution_config()
            logger.info(f"Provider override set for {provider}: force_simulation={force_simulation}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting provider override: {e}")
            return False