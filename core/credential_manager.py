import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages credential injection and validation for all providers"""
    
    def __init__(self, credentials_path: str = "./config/api_credentials.json"):
        self.credentials_path = Path(credentials_path)
        self.credentials_config = {}
        self._load_credentials()
        
    def _load_credentials(self):
        """Load credentials configuration from file"""
        try:
            if self.credentials_path.exists():
                with open(self.credentials_path, 'r') as f:
                    self.credentials_config = json.load(f)
                logger.info("Credentials configuration loaded")
            else:
                logger.warning("Credentials configuration file not found")
                self.credentials_config = {}
        except Exception as e:
            logger.error(f"Error loading credentials configuration: {e}")
            self.credentials_config = {}
    
    def _save_credentials(self):
        """Save credentials configuration to file"""
        try:
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.credentials_path, 'w') as f:
                json.dump(self.credentials_config, f, indent=2)
            logger.info("Credentials configuration saved")
        except Exception as e:
            logger.error(f"Error saving credentials configuration: {e}")
    
    def detect_environment_variables(self) -> Dict[str, Any]:
        """Detect and validate environment variables for credentials"""
        env_status = {}
        
        # Define expected environment variables for each provider
        provider_env_vars = {
            "tradestation": {
                "TRADESTATION_CLIENT_ID": "client_id",
                "TRADESTATION_CLIENT_SECRET": "client_secret"
            },
            "polygon_io": {
                "POLYGON_API_KEY": "api_key"
            },
            "alpha_vantage": {
                "ALPHA_VANTAGE_API_KEY": "api_key"
            },
            "defi": {
                "DEFI_WALLET_ADDRESS": "wallet_address",
                "DEFI_PRIVATE_KEY": "private_key"
            }
        }
        
        for provider, env_vars in provider_env_vars.items():
            provider_status = {
                "provider": provider,
                "required_vars": list(env_vars.keys()),
                "found_vars": [],
                "missing_vars": [],
                "status": "unknown"
            }
            
            for env_var, config_key in env_vars.items():
                if os.getenv(env_var):
                    provider_status["found_vars"].append(env_var)
                else:
                    provider_status["missing_vars"].append(env_var)
            
            # Determine status
            if not provider_status["missing_vars"]:
                provider_status["status"] = "fully_configured"
            elif provider_status["found_vars"]:
                provider_status["status"] = "partially_configured"
            else:
                provider_status["status"] = "not_configured"
            
            env_status[provider] = provider_status
        
        return env_status
    
    def inject_credentials_from_env(self) -> Dict[str, Any]:
        """Inject credentials from environment variables"""
        injection_results = {
            "successful_injections": [],
            "failed_injections": [],
            "updated_providers": []
        }
        
        # Provider mappings
        provider_mappings = {
            "tradestation": {
                "TRADESTATION_CLIENT_ID": "client_id",
                "TRADESTATION_CLIENT_SECRET": "client_secret"
            },
            "polygon_io": {
                "POLYGON_API_KEY": "api_key"
            },
            "alpha_vantage": {
                "ALPHA_VANTAGE_API_KEY": "api_key"
            },
            "defi": {
                "DEFI_WALLET_ADDRESS": "wallet_address",
                "DEFI_PRIVATE_KEY": "private_key"
            }
        }
        
        for provider, env_mappings in provider_mappings.items():
            try:
                if provider not in self.credentials_config:
                    self.credentials_config[provider] = {}
                
                updated = False
                for env_var, config_key in env_mappings.items():
                    env_value = os.getenv(env_var)
                    if env_value and env_value != self.credentials_config[provider].get(config_key):
                        # Replace environment variable placeholder with actual value
                        old_value = self.credentials_config[provider].get(config_key, "not_set")
                        self.credentials_config[provider][config_key] = env_value
                        
                        injection_results["successful_injections"].append({
                            "provider": provider,
                            "env_var": env_var,
                            "config_key": config_key,
                            "old_value": old_value if not old_value.startswith("${") else "placeholder",
                            "injected": True
                        })
                        updated = True
                        logger.info(f"Injected {env_var} for {provider}")
                
                if updated:
                    injection_results["updated_providers"].append(provider)
                    
            except Exception as e:
                injection_results["failed_injections"].append({
                    "provider": provider,
                    "error": str(e)
                })
                logger.error(f"Error injecting credentials for {provider}: {e}")
        
        # Save updated credentials
        if injection_results["updated_providers"]:
            self._save_credentials()
        
        return injection_results
    
    def validate_provider_credentials(self, provider: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate credentials for a specific provider"""
        if provider not in self.credentials_config:
            return False, f"No credentials configured for {provider}", {}
        
        provider_creds = self.credentials_config[provider]
        validation_result = {
            "provider": provider,
            "credentials_found": [],
            "credentials_missing": [],
            "placeholder_values": [],
            "validation_status": "unknown"
        }
        
        # Define required credentials per provider
        required_creds = {
            "tradestation": ["client_id", "client_secret"],
            "polygon_io": ["api_key"],
            "alpha_vantage": ["api_key"],
            "defi": ["wallet_address"]  # private_key is optional for simulation
        }
        
        if provider not in required_creds:
            return False, f"Unknown provider: {provider}", validation_result
        
        # Check each required credential
        for cred_key in required_creds[provider]:
            cred_value = provider_creds.get(cred_key)
            
            if not cred_value:
                validation_result["credentials_missing"].append(cred_key)
            elif cred_value.startswith("${") and cred_value.endswith("}"):
                validation_result["placeholder_values"].append(cred_key)
            elif cred_value in ["your_key_here", "your_client_id_here", "your_client_secret_here"]:
                validation_result["placeholder_values"].append(cred_key)
            else:
                validation_result["credentials_found"].append(cred_key)
        
        # Determine overall validation status
        if not validation_result["credentials_missing"] and not validation_result["placeholder_values"]:
            validation_result["validation_status"] = "fully_valid"
            return True, f"All credentials valid for {provider}", validation_result
        elif validation_result["credentials_found"]:
            validation_result["validation_status"] = "partially_valid"
            return False, f"Some credentials missing/invalid for {provider}", validation_result
        else:
            validation_result["validation_status"] = "invalid"
            return False, f"No valid credentials for {provider}", validation_result
    
    def get_credential_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive credential status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment_variables": self.detect_environment_variables(),
            "provider_validations": {},
            "overall_status": {
                "total_providers": 0,
                "fully_configured": 0,
                "partially_configured": 0,
                "not_configured": 0
            },
            "recommendations": []
        }
        
        # Validate each provider
        providers = ["tradestation", "polygon_io", "alpha_vantage", "defi"]
        for provider in providers:
            is_valid, message, details = self.validate_provider_credentials(provider)
            report["provider_validations"][provider] = {
                "is_valid": is_valid,
                "message": message,
                "details": details
            }
            
            # Update overall status
            report["overall_status"]["total_providers"] += 1
            if details.get("validation_status") == "fully_valid":
                report["overall_status"]["fully_configured"] += 1
            elif details.get("validation_status") == "partially_valid":
                report["overall_status"]["partially_configured"] += 1
            else:
                report["overall_status"]["not_configured"] += 1
        
        # Generate recommendations
        if report["overall_status"]["not_configured"] > 0:
            report["recommendations"].append("Set up environment variables for missing provider credentials")
        
        if report["overall_status"]["partially_configured"] > 0:
            report["recommendations"].append("Complete credential configuration for partially configured providers")
        
        if report["overall_status"]["fully_configured"] == report["overall_status"]["total_providers"]:
            report["recommendations"].append("All providers configured - system ready for credential validation")
        
        return report
    
    def create_env_template(self) -> str:
        """Create environment variable template file"""
        template = """# AutomationBot Environment Variables
# Copy this file to .env and fill in your actual credentials

# TradeStation API Credentials
TRADESTATION_CLIENT_ID=your_client_id_here
TRADESTATION_CLIENT_SECRET=your_client_secret_here

# Polygon.io API Key
POLYGON_API_KEY=your_polygon_api_key_here

# Alpha Vantage API Key (Optional)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# DeFi Wallet Configuration (Optional - for DeFi execution)
DEFI_WALLET_ADDRESS=your_wallet_address_here
DEFI_PRIVATE_KEY=your_private_key_here

# Usage Instructions:
# 1. Replace 'your_*_here' values with your actual credentials
# 2. Source this file or set these environment variables in your system
# 3. Restart the AutomationBot system
# 4. Use /credentials/inject to inject credentials from environment
"""
        
        template_path = Path("./config/env_template.txt")
        try:
            template_path.write_text(template)
            logger.info(f"Environment template created: {template_path}")
            return str(template_path)
        except Exception as e:
            logger.error(f"Error creating environment template: {e}")
            return f"Error: {str(e)}"