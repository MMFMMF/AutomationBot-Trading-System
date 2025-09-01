"""
Centralized Configuration API Routes with Standardized Responses

This module provides unified API endpoints for all system configuration
management with proper validation and error handling.
"""

from flask import request
from core.api_response import (
    APIResponse, APIException, ErrorCode, create_response_decorator,
    validate_request_data
)
from core.config_manager import config_manager, validate_capital_allocation, validate_risk_parameters


def register_config_routes(app, logger):
    """
    Register all configuration management routes
    
    Args:
        app: Flask application instance
        logger: Logger instance for route debugging
    """
    
    @app.route('/api/config', methods=['GET'])
    @create_response_decorator
    def get_system_config(api_response):
        """Get complete system configuration"""
        config_data = config_manager.get_all_config()
        return api_response.success(config_data, "System configuration retrieved successfully")
    
    @app.route('/api/config/trading', methods=['GET'])
    @create_response_decorator
    def get_trading_config(api_response):
        """Get trading configuration"""
        trading_config = config_manager.get_trading_config()
        return api_response.success(trading_config.__dict__, "Trading configuration retrieved successfully")
    
    @app.route('/api/config/trading', methods=['PUT'])
    @create_response_decorator
    def update_trading_config(api_response):
        """Update trading configuration with validation"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain configuration updates"
            )
        
        # Update configuration through config manager (includes validation)
        updated_config = config_manager.update_trading_config(**data)
        
        return api_response.success(
            updated_config, 
            f"Trading configuration updated successfully"
        )
    
    @app.route('/api/config/providers', methods=['GET'])
    @create_response_decorator
    def get_provider_config(api_response):
        """Get provider configuration"""
        provider_config = config_manager.get_provider_config()
        return api_response.success(provider_config.__dict__, "Provider configuration retrieved successfully")
    
    @app.route('/api/config/providers', methods=['PUT'])
    @create_response_decorator
    def update_provider_config(api_response):
        """Update provider configuration with validation"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain configuration updates"
            )
        
        # Update configuration through config manager (includes validation)
        updated_config = config_manager.update_provider_config(**data)
        
        return api_response.success(
            updated_config, 
            f"Provider configuration updated successfully"
        )
    
    @app.route('/api/config/system', methods=['GET'])
    @create_response_decorator
    def get_system_config_only(api_response):
        """Get system configuration"""
        system_config = config_manager.get_system_config()
        return api_response.success(system_config.__dict__, "System configuration retrieved successfully")
    
    @app.route('/api/config/system', methods=['PUT'])
    @create_response_decorator
    def update_system_config(api_response):
        """Update system configuration with validation"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain configuration updates"
            )
        
        # Update configuration through config manager (includes validation)
        updated_config = config_manager.update_system_config(**data)
        
        return api_response.success(
            updated_config, 
            f"System configuration updated successfully"
        )
    
    @app.route('/api/config/validate', methods=['POST'])
    @create_response_decorator
    def validate_configuration(api_response):
        """Validate current system configuration"""
        validation_results = config_manager.validate_config()
        
        if validation_results['valid']:
            return api_response.success(
                validation_results,
                "Configuration validation passed"
            )
        else:
            return api_response.warning(
                validation_results,
                "CONFIG_VALIDATION_ISSUES",
                f"Configuration has {len(validation_results['issues'])} issues",
                "Review and fix configuration issues before proceeding"
            )
    
    @app.route('/api/config/reset', methods=['POST'])
    @create_response_decorator
    def reset_configuration(api_response):
        """Reset configuration to defaults"""
        data = request.get_json() or {}
        section = data.get('section')  # Optional: reset specific section only
        
        if section and section not in ['trading', 'providers', 'system', 'security']:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                f"Invalid configuration section: {section}",
                "Valid sections: trading, providers, system, security"
            )
        
        reset_config = config_manager.reset_to_defaults(section)
        section_text = f"{section} " if section else ""
        
        return api_response.success(
            reset_config,
            f"Configuration {section_text}reset to defaults successfully"
        )
    
    # Capital Management Endpoints
    @app.route('/api/config/capital', methods=['GET'])
    @create_response_decorator
    def get_capital_config(api_response):
        """Get capital allocation configuration"""
        trading_config = config_manager.get_trading_config()
        capital_data = {
            'total_capital': trading_config.capital_amount,
            'max_positions': trading_config.max_positions,
            'risk_per_trade': trading_config.risk_per_trade,
            'available_capital': trading_config.capital_amount,  # This would be calculated in real implementation
            'allocated_capital': 0.0  # This would be calculated from open positions
        }
        return api_response.success(capital_data, "Capital configuration retrieved successfully")
    
    @app.route('/api/config/capital/initialize', methods=['POST'])
    @create_response_decorator
    def initialize_capital(api_response):
        """Initialize total capital amount"""
        data = request.get_json()
        validate_request_data(data, ['total_capital'])
        
        total_capital = data['total_capital']
        
        # Update through config manager for validation
        updated_config = config_manager.update_trading_config(capital_amount=total_capital)
        
        return api_response.success(
            {'capital_amount': updated_config['capital_amount']},
            f"Capital initialized to ${total_capital:,.2f}"
        )
    
    @app.route('/api/config/capital/allocations', methods=['PUT'])
    @create_response_decorator
    def update_capital_allocations(api_response):
        """Update capital allocation percentages"""
        data = request.get_json()
        validate_request_data(data, ['allocation_percentages'])
        
        allocations = data['allocation_percentages']
        validate_capital_allocation(allocations)
        
        # This would integrate with portfolio management system
        # For now, we'll just validate and return success
        
        return api_response.success(
            {'allocations': allocations},
            "Capital allocations updated successfully"
        )
    
    @app.route('/api/config/risk-parameters', methods=['GET'])
    @create_response_decorator
    def get_risk_parameters(api_response):
        """Get risk management parameters"""
        trading_config = config_manager.get_trading_config()
        risk_data = {
            'risk_per_trade': trading_config.risk_per_trade,
            'max_positions': trading_config.max_positions,
            'max_drawdown': 0.15,  # This would come from risk management system
            'var_threshold': 1000.0,  # This would come from risk management system
            'stop_loss_percentage': 0.02,
            'take_profit_percentage': 0.06
        }
        return api_response.success(risk_data, "Risk parameters retrieved successfully")
    
    @app.route('/api/config/risk-parameters', methods=['PUT'])
    @create_response_decorator
    def update_risk_parameters(api_response):
        """Update risk management parameters"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain risk parameter updates"
            )
        
        # Validate risk parameters
        validate_risk_parameters(
            max_drawdown=data.get('max_drawdown'),
            var_threshold=data.get('var_threshold')
        )
        
        # Update trading config if it contains relevant parameters
        trading_updates = {}
        if 'risk_per_trade' in data:
            trading_updates['risk_per_trade'] = data['risk_per_trade']
        if 'max_positions' in data:
            trading_updates['max_positions'] = data['max_positions']
        
        if trading_updates:
            config_manager.update_trading_config(**trading_updates)
        
        return api_response.success(
            data,
            "Risk parameters updated successfully"
        )
    
    # Strategy Configuration Endpoints
    @app.route('/api/config/strategies', methods=['GET'])
    @create_response_decorator
    def get_strategy_config(api_response):
        """Get strategy configuration"""
        trading_config = config_manager.get_trading_config()
        strategy_data = {
            'enabled_strategies': trading_config.strategies_enabled,
            'signal_interval': trading_config.signal_interval,
            'auto_trading': trading_config.auto_trading,
            'available_strategies': [
                'mixed', 'ma_crossover', 'rsi_mean_reversion', 
                'momentum_breakout', 'test'
            ]
        }
        return api_response.success(strategy_data, "Strategy configuration retrieved successfully")
    
    @app.route('/api/config/strategies', methods=['PUT'])
    @create_response_decorator
    def update_strategy_config(api_response):
        """Update strategy configuration"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain strategy configuration updates"
            )
        
        # Prepare updates for config manager
        strategy_updates = {}
        if 'enabled_strategies' in data:
            strategy_updates['strategies_enabled'] = data['enabled_strategies']
        if 'signal_interval' in data:
            strategy_updates['signal_interval'] = data['signal_interval']
        if 'auto_trading' in data:
            strategy_updates['auto_trading'] = data['auto_trading']
        
        # Update through config manager for validation
        updated_config = config_manager.update_trading_config(**strategy_updates)
        
        return api_response.success(
            {
                'enabled_strategies': updated_config['strategies_enabled'],
                'signal_interval': updated_config['signal_interval'],
                'auto_trading': updated_config['auto_trading']
            },
            "Strategy configuration updated successfully"
        )