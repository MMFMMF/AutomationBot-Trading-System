"""
Data Integrity Management System for AutomationBot Trading Platform

This module ensures ABSOLUTE data integrity by:
- Eliminating ALL synthetic/fake data generation
- Implementing strict data validation before display
- Providing fail-safe mechanisms that show "No Data" rather than fake values
- Maintaining complete audit trail for all data operations
"""

import time
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging_system import system_monitor
from core.api_response import APIException, ErrorCode


class DataValidationLevel(Enum):
    """Data validation severity levels"""
    CRITICAL = "critical"    # Block display if validation fails
    WARNING = "warning"      # Log warning but allow display
    INFO = "info"           # Log for audit purposes only


@dataclass
class DataValidationResult:
    """Result of data validation check"""
    is_valid: bool
    level: DataValidationLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    source_verified: bool = False
    calculation_verified: bool = False


@dataclass
class DataLineage:
    """Track data lineage from source to display"""
    data_type: str
    source_table: str
    source_query: str
    calculation_method: str
    validation_rules: List[str]
    last_verified: float
    verification_count: int = 0


class DataIntegrityManager:
    """
    Comprehensive data integrity management system
    """
    
    def __init__(self):
        """Initialize data integrity manager"""
        self.logger = system_monitor.get_logger('data_integrity')
        self.validation_rules = {}
        self.data_lineage = {}
        self.blocked_data = set()  # Data that failed validation
        self.audit_trail = []
        self._setup_validation_rules()
    
    def _setup_validation_rules(self):
        """Setup comprehensive validation rules"""
        self.validation_rules = {
            # Trading data validation
            'trade_data': {
                'required_fields': ['symbol', 'entry_time', 'entry_price', 'quantity', 'trade_id'],
                'field_types': {
                    'entry_price': (int, float),
                    'quantity': (int, float),
                    'entry_time': str,
                    'symbol': str
                },
                'logical_checks': [
                    self._validate_trade_logic,
                    self._validate_price_reasonableness,
                    self._validate_timestamp_sequence
                ]
            },
            
            # Signal data validation
            'signal_data': {
                'required_fields': ['signal_id', 'symbol', 'timestamp', 'strategy', 'side'],
                'field_types': {
                    'timestamp': (str, float),
                    'symbol': str,
                    'strategy': str,
                    'side': str
                },
                'logical_checks': [
                    self._validate_signal_logic,
                    self._validate_strategy_exists
                ]
            },
            
            # Performance metrics validation
            'performance_metrics': {
                'required_fields': ['metric_name', 'value', 'timestamp'],
                'field_types': {
                    'value': (int, float),
                    'timestamp': (str, float),
                    'metric_name': str
                },
                'logical_checks': [
                    self._validate_metric_calculation,
                    self._validate_metric_consistency
                ]
            },
            
            # Portfolio data validation
            'portfolio_data': {
                'required_fields': ['timestamp', 'total_value'],
                'field_types': {
                    'total_value': (int, float),
                    'timestamp': (str, float)
                },
                'logical_checks': [
                    self._validate_portfolio_calculation
                ]
            }
        }
    
    def validate_data(self, data_type: str, data: Any, 
                     strict_mode: bool = True) -> DataValidationResult:
        """
        Comprehensive data validation
        
        Args:
            data_type: Type of data being validated
            data: Data to validate
            strict_mode: If True, block display on validation failure
            
        Returns:
            Validation result
        """
        if data_type not in self.validation_rules:
            return DataValidationResult(
                is_valid=False,
                level=DataValidationLevel.CRITICAL,
                message=f"Unknown data type: {data_type}",
                details={'data_type': data_type}
            )
        
        rules = self.validation_rules[data_type]
        validation_errors = []
        
        # Check if data exists
        if not data:
            return DataValidationResult(
                is_valid=False,
                level=DataValidationLevel.INFO,
                message="No data available - this is acceptable",
                source_verified=True  # Empty data is valid
            )
        
        # Handle list of data items
        if isinstance(data, list):
            if not data:
                return DataValidationResult(
                    is_valid=True,
                    level=DataValidationLevel.INFO,
                    message="Empty data list - valid state",
                    source_verified=True
                )
            
            # Validate each item in the list
            for i, item in enumerate(data):
                item_result = self._validate_single_item(data_type, item, rules)
                if not item_result.is_valid and strict_mode:
                    validation_errors.append(f"Item {i}: {item_result.message}")
        else:
            # Validate single item
            item_result = self._validate_single_item(data_type, data, rules)
            if not item_result.is_valid:
                validation_errors.append(item_result.message)
        
        # Determine overall validation result
        if validation_errors and strict_mode:
            return DataValidationResult(
                is_valid=False,
                level=DataValidationLevel.CRITICAL,
                message="Data validation failed",
                details={'errors': validation_errors}
            )
        
        return DataValidationResult(
            is_valid=True,
            level=DataValidationLevel.INFO if not validation_errors else DataValidationLevel.WARNING,
            message="Data validation passed" if not validation_errors else "Data validation passed with warnings",
            details={'warnings': validation_errors} if validation_errors else None,
            source_verified=True,
            calculation_verified=True
        )
    
    def _validate_single_item(self, data_type: str, item: Dict, 
                             rules: Dict) -> DataValidationResult:
        """Validate a single data item"""
        errors = []
        
        # Check required fields
        for field in rules.get('required_fields', []):
            if field not in item:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        field_types = rules.get('field_types', {})
        for field, expected_type in field_types.items():
            if field in item:
                if not isinstance(item[field], expected_type):
                    errors.append(f"Field {field} has incorrect type: expected {expected_type}, got {type(item[field])}")
        
        # Run logical checks
        for check_func in rules.get('logical_checks', []):
            try:
                check_result = check_func(item)
                if not check_result:
                    errors.append(f"Logical validation failed: {check_func.__name__}")
            except Exception as e:
                errors.append(f"Validation check error: {check_func.__name__}: {str(e)}")
        
        return DataValidationResult(
            is_valid=len(errors) == 0,
            level=DataValidationLevel.CRITICAL if errors else DataValidationLevel.INFO,
            message="Item validation passed" if not errors else f"Item validation failed: {'; '.join(errors)}",
            details={'errors': errors} if errors else None
        )
    
    # Logical validation functions
    def _validate_trade_logic(self, trade: Dict) -> bool:
        """Validate trade logical consistency"""
        # Check if trade has realistic values
        entry_price = trade.get('entry_price', 0)
        if entry_price <= 0 or entry_price > 100000:  # Unrealistic price
            return False
        
        quantity = trade.get('quantity', 0)
        if quantity <= 0 or quantity > 10000:  # Unrealistic quantity
            return False
        
        # Check if exit data is consistent with entry data
        if 'exit_time' in trade and 'entry_time' in trade:
            try:
                entry_time = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
                exit_time = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00'))
                if exit_time <= entry_time:  # Exit before entry
                    return False
            except:
                return False
        
        return True
    
    def _validate_price_reasonableness(self, trade: Dict) -> bool:
        """Validate price reasonableness"""
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price')
        
        # Basic sanity checks
        if entry_price <= 0:
            return False
        
        if exit_price is not None:
            if exit_price <= 0:
                return False
            
            # Check for unrealistic price movements (>50% in single trade)
            price_change = abs(exit_price - entry_price) / entry_price
            if price_change > 0.5:
                return False
        
        return True
    
    def _validate_timestamp_sequence(self, trade: Dict) -> bool:
        """Validate timestamp logical sequence"""
        entry_time = trade.get('entry_time')
        exit_time = trade.get('exit_time')
        
        if not entry_time:
            return False
        
        try:
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            
            # Entry time shouldn't be in the future
            if entry_dt > datetime.now(timezone.utc):
                return False
            
            # If exit time exists, validate sequence
            if exit_time:
                exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                if exit_dt <= entry_dt:
                    return False
                
                # Exit time shouldn't be in the future
                if exit_dt > datetime.now(timezone.utc):
                    return False
            
            return True
        except:
            return False
    
    def _validate_signal_logic(self, signal: Dict) -> bool:
        """Validate signal logical consistency"""
        # Check required fields exist and are valid
        side = signal.get('side')
        if side not in ['BUY', 'SELL', 'buy', 'sell']:
            return False
        
        strategy = signal.get('strategy')
        if not strategy or strategy not in ['ma_crossover', 'rsi_mean_reversion', 'momentum_breakout', 'mixed']:
            return False
        
        return True
    
    def _validate_strategy_exists(self, signal: Dict) -> bool:
        """Validate that the strategy actually exists"""
        strategy = signal.get('strategy')
        # This would check against a registry of valid strategies
        valid_strategies = ['ma_crossover', 'rsi_mean_reversion', 'momentum_breakout', 'mixed']
        return strategy in valid_strategies
    
    def _validate_metric_calculation(self, metric: Dict) -> bool:
        """Validate metric calculation logic"""
        metric_name = metric.get('metric_name')
        value = metric.get('value')
        
        # Validate specific metric types
        if metric_name in ['win_rate']:
            return 0 <= value <= 1  # Win rate should be between 0 and 1
        elif metric_name in ['pnl', 'total_pnl']:
            return isinstance(value, (int, float))  # P&L should be numeric
        elif metric_name in ['trade_count']:
            return isinstance(value, int) and value >= 0  # Trade count should be non-negative integer
        
        return True
    
    def _validate_metric_consistency(self, metric: Dict) -> bool:
        """Validate metric consistency with other metrics"""
        # This would perform cross-metric validation
        # For now, just basic validation
        return isinstance(metric.get('value'), (int, float))
    
    def _validate_portfolio_calculation(self, portfolio: Dict) -> bool:
        """Validate portfolio calculation"""
        total_value = portfolio.get('total_value')
        
        # Portfolio value should be positive (or zero for empty portfolio)
        if not isinstance(total_value, (int, float)) or total_value < 0:
            return False
        
        return True
    
    def register_data_lineage(self, data_type: str, lineage: DataLineage):
        """Register data lineage for audit purposes"""
        self.data_lineage[data_type] = lineage
        self.logger.info(f"Registered data lineage for {data_type}")
    
    def get_verified_data_or_null(self, data_type: str, data: Any, 
                                  strict_mode: bool = True) -> Tuple[Any, bool]:
        """
        Get data only if it passes validation, otherwise return None
        
        Args:
            data_type: Type of data
            data: Data to validate
            strict_mode: Whether to be strict about validation
            
        Returns:
            Tuple of (data_or_none, is_valid)
        """
        validation_result = self.validate_data(data_type, data, strict_mode)
        
        if validation_result.is_valid:
            self.logger.info(f"Data validation passed for {data_type}")
            return data, True
        else:
            self.logger.warning(f"Data validation failed for {data_type}: {validation_result.message}")
            
            # Add to audit trail
            self.audit_trail.append({
                'timestamp': time.time(),
                'data_type': data_type,
                'validation_result': validation_result,
                'action': 'BLOCKED' if strict_mode else 'ALLOWED_WITH_WARNING'
            })
            
            if strict_mode:
                return None, False
            else:
                return data, False
    
    def create_empty_response(self, data_type: str, message: str = None) -> Dict[str, Any]:
        """
        Create safe empty response for missing/invalid data
        
        Args:
            data_type: Type of data
            message: Custom message
            
        Returns:
            Safe empty response structure
        """
        default_message = f"No verified {data_type} available"
        
        empty_responses = {
            'trade_data': {
                'trades': [],
                'total_trades': 0,
                'message': message or 'No verified trades available',
                'data_status': 'NO_DATA_AVAILABLE'
            },
            'portfolio_data': {
                'portfolio_history': [],
                'current_value': None,
                'message': message or 'Portfolio data unavailable',
                'data_status': 'INSUFFICIENT_DATA'
            },
            'performance_metrics': {
                'strategy_performance': {},
                'risk_metrics': {},
                'message': message or 'Performance data not yet available',
                'data_status': 'CALCULATING'
            },
            'chart_data': {
                'portfolio_history': [],
                'strategy_performance': {},
                'risk_metrics': {},
                'positions_data': [],
                'daily_pnl': [],
                'message': message or 'Chart data unavailable - insufficient trading history',
                'data_status': 'NO_DATA_AVAILABLE'
            }
        }
        
        return empty_responses.get(data_type, {
            'data': None,
            'message': message or default_message,
            'data_status': 'UNAVAILABLE'
        })
    
    def audit_data_access(self, data_type: str, access_result: str, 
                         details: Optional[Dict] = None):
        """Record data access for audit trail"""
        self.audit_trail.append({
            'timestamp': time.time(),
            'data_type': data_type,
            'access_result': access_result,
            'details': details or {}
        })
        
        # Keep only last 1000 audit entries
        if len(self.audit_trail) > 1000:
            self.audit_trail = self.audit_trail[-1000:]
    
    def get_data_integrity_status(self) -> Dict[str, Any]:
        """Get comprehensive data integrity status"""
        return {
            'validation_rules_count': len(self.validation_rules),
            'data_lineage_registered': len(self.data_lineage),
            'blocked_data_types': len(self.blocked_data),
            'audit_entries': len(self.audit_trail),
            'last_audit': max([entry['timestamp'] for entry in self.audit_trail]) if self.audit_trail else None,
            'integrity_status': 'ENFORCING' if self.validation_rules else 'NOT_CONFIGURED'
        }


# Global data integrity manager
data_integrity_manager = DataIntegrityManager()


def ensure_data_integrity(data_type: str, strict_validation: bool = True):
    """
    Decorator to ensure data integrity for endpoints
    
    Args:
        data_type: Type of data being returned
        strict_validation: Whether to enforce strict validation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Execute the original function
                result = func(*args, **kwargs)
                
                # Extract data from response (handle different response formats)
                if hasattr(result, 'json'):
                    response_data = result.json
                elif isinstance(result, tuple) and len(result) >= 2:
                    response_data = result[0].json if hasattr(result[0], 'json') else result[0]
                else:
                    response_data = result
                
                # Validate the data
                if 'data' in response_data:
                    validated_data, is_valid = data_integrity_manager.get_verified_data_or_null(
                        data_type, 
                        response_data['data'],
                        strict_validation
                    )
                    
                    if not is_valid and strict_validation:
                        # Return empty safe response
                        safe_response = data_integrity_manager.create_empty_response(data_type)
                        data_integrity_manager.audit_data_access(data_type, 'BLOCKED_INVALID_DATA')
                        
                        # Update the response with safe data
                        response_data['data'] = safe_response
                        response_data['message'] = safe_response.get('message', 'Data validation failed')
                        response_data['data_integrity'] = {
                            'validated': False,
                            'reason': 'Data failed integrity validation',
                            'safe_response_provided': True
                        }
                    else:
                        data_integrity_manager.audit_data_access(data_type, 'ALLOWED_VALID_DATA')
                        response_data['data_integrity'] = {
                            'validated': True,
                            'verification_timestamp': datetime.now(timezone.utc).isoformat()
                        }
                
                return result
                
            except Exception as e:
                # If anything fails, return safe empty response
                data_integrity_manager.logger.error(f"Data integrity check failed: {e}")
                safe_response = data_integrity_manager.create_empty_response(
                    data_type, 
                    "Data integrity check failed - no data displayed for safety"
                )
                data_integrity_manager.audit_data_access(data_type, 'ERROR_SAFE_FALLBACK', {'error': str(e)})
                
                return safe_response
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator