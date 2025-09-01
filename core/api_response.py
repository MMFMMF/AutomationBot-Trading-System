"""
Standardized API Response System for AutomationBot Trading Platform

This module provides consistent response formatting, error handling, and 
metadata management across all API endpoints.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from flask import jsonify, Response
from enum import Enum


class ResponseStatus(Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ErrorCode(Enum):
    """Standardized error codes for consistent error handling"""
    # General errors
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    
    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    
    # Trading errors
    INSUFFICIENT_CAPITAL = "INSUFFICIENT_CAPITAL"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    MARKET_CLOSED = "MARKET_CLOSED"
    TRADING_SUSPENDED = "TRADING_SUSPENDED"
    INVALID_STRATEGY = "INVALID_STRATEGY"
    
    # System errors
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"


class APIResponse:
    """
    Standardized API response builder with consistent formatting
    
    All API responses follow this format:
    {
        "status": "success|error|warning|partial",
        "timestamp": "ISO 8601 timestamp",
        "data": {}, // Response payload (success only)
        "error": {  // Error details (error only)
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": "Additional context"
        },
        "metadata": {
            "version": "API version",
            "execution_time_ms": 123,
            "request_id": "unique_request_id"
        }
    }
    """
    
    def __init__(self, request_start_time: Optional[float] = None):
        """
        Initialize API response builder
        
        Args:
            request_start_time: Start time for execution time calculation
        """
        self.request_start_time = request_start_time or time.time()
        self.request_id = str(uuid.uuid4())[:8]
        self.api_version = "2.1"
    
    def success(self, data: Any = None, message: Optional[str] = None) -> tuple[Response, int]:
        """
        Create a successful response
        
        Args:
            data: Response data payload
            message: Optional success message
            
        Returns:
            Tuple of (Flask Response, HTTP status code)
        """
        response_data = {
            "status": ResponseStatus.SUCCESS.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
            "metadata": self._build_metadata()
        }
        
        if message:
            response_data["message"] = message
            
        return jsonify(response_data), 200
    
    def error(self, 
              error_code: ErrorCode, 
              message: str,
              details: Optional[str] = None,
              http_status: int = 400,
              data: Optional[Dict] = None) -> tuple[Response, int]:
        """
        Create an error response
        
        Args:
            error_code: Standardized error code
            message: Human-readable error message
            details: Additional error context
            http_status: HTTP status code (default: 400)
            data: Optional partial data for partial failures
            
        Returns:
            Tuple of (Flask Response, HTTP status code)
        """
        response_data = {
            "status": ResponseStatus.ERROR.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": {
                "code": error_code.value,
                "message": message
            },
            "metadata": self._build_metadata()
        }
        
        if details:
            response_data["error"]["details"] = details
            
        if data:
            response_data["data"] = data
            
        return jsonify(response_data), http_status
    
    def warning(self, 
                data: Any,
                warning_code: str,
                message: str,
                details: Optional[str] = None) -> tuple[Response, int]:
        """
        Create a warning response (success with warnings)
        
        Args:
            data: Response data payload
            warning_code: Warning identifier
            message: Warning message
            details: Additional warning context
            
        Returns:
            Tuple of (Flask Response, HTTP status code)
        """
        response_data = {
            "status": ResponseStatus.WARNING.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "warning": {
                "code": warning_code,
                "message": message
            },
            "metadata": self._build_metadata()
        }
        
        if details:
            response_data["warning"]["details"] = details
            
        return jsonify(response_data), 200
    
    def partial(self,
                data: Any,
                errors: list,
                message: str = "Request partially completed") -> tuple[Response, int]:
        """
        Create a partial success response
        
        Args:
            data: Successfully processed data
            errors: List of errors that occurred
            message: Partial success message
            
        Returns:
            Tuple of (Flask Response, HTTP status code)
        """
        response_data = {
            "status": ResponseStatus.PARTIAL.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "message": message,
            "errors": errors,
            "metadata": self._build_metadata()
        }
        
        return jsonify(response_data), 207  # Multi-Status
    
    def _build_metadata(self) -> Dict[str, Any]:
        """Build response metadata"""
        execution_time = int((time.time() - self.request_start_time) * 1000)
        
        return {
            "version": self.api_version,
            "execution_time_ms": execution_time,
            "request_id": self.request_id
        }


class APIException(Exception):
    """
    Custom exception for API errors with structured error information
    """
    
    def __init__(self, 
                 error_code: ErrorCode,
                 message: str,
                 details: Optional[str] = None,
                 http_status: int = 400,
                 data: Optional[Dict] = None):
        """
        Initialize API exception
        
        Args:
            error_code: Standardized error code
            message: Human-readable error message
            details: Additional error context
            http_status: HTTP status code
            data: Optional partial data
        """
        self.error_code = error_code
        self.message = message
        self.details = details
        self.http_status = http_status
        self.data = data
        super().__init__(message)
    
    def to_response(self, api_response: APIResponse) -> tuple[Response, int]:
        """Convert exception to API response"""
        return api_response.error(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            http_status=self.http_status,
            data=self.data
        )


def handle_api_exception(e: Exception, api_response: APIResponse) -> tuple[Response, int]:
    """
    Global exception handler for converting exceptions to standardized responses
    
    Args:
        e: Exception that occurred
        api_response: API response builder
        
    Returns:
        Standardized error response
    """
    if isinstance(e, APIException):
        return e.to_response(api_response)
    
    # Map common exceptions to API errors
    if isinstance(e, ValueError):
        return api_response.error(
            ErrorCode.INVALID_PARAMETER,
            "Invalid parameter value",
            str(e)
        )
    elif isinstance(e, KeyError):
        return api_response.error(
            ErrorCode.MISSING_PARAMETER,
            "Required parameter missing",
            str(e)
        )
    elif isinstance(e, FileNotFoundError):
        return api_response.error(
            ErrorCode.RESOURCE_NOT_FOUND,
            "Requested resource not found",
            str(e)
        )
    elif isinstance(e, PermissionError):
        return api_response.error(
            ErrorCode.FORBIDDEN,
            "Access denied",
            str(e),
            http_status=403
        )
    else:
        # Generic internal error
        return api_response.error(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred",
            str(e),
            http_status=500
        )


def validate_request_data(data: Dict, required_fields: list, optional_fields: list = None) -> None:
    """
    Validate request data and raise APIException if invalid
    
    Args:
        data: Request data to validate
        required_fields: List of required field names
        optional_fields: List of optional field names (for documentation)
        
    Raises:
        APIException: If validation fails
    """
    if not isinstance(data, dict):
        raise APIException(
            ErrorCode.INVALID_REQUEST_FORMAT,
            "Request body must be valid JSON object"
        )
    
    # Check required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise APIException(
            ErrorCode.MISSING_PARAMETER,
            f"Missing required fields: {', '.join(missing_fields)}",
            f"Required fields: {', '.join(required_fields)}"
        )
    
    # Validate field types if needed (can be extended)
    for field in required_fields:
        if data[field] is None or data[field] == "":
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                f"Field '{field}' cannot be empty"
            )


def create_response_decorator(func):
    """
    Decorator to automatically handle API responses and exceptions
    
    Usage:
        @app.route('/endpoint')
        @create_response_decorator
        def my_endpoint():
            # Function automatically gets APIResponse as first argument
            # Exceptions are automatically converted to error responses
            pass
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        api_response = APIResponse(start_time)
        
        try:
            # Inject api_response as first argument
            return func(api_response, *args, **kwargs)
        except Exception as e:
            return handle_api_exception(e, api_response)
    
    wrapper.__name__ = func.__name__
    return wrapper


# Common validation patterns
def validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol"""
    if not symbol or not isinstance(symbol, str):
        raise APIException(
            ErrorCode.INVALID_PARAMETER,
            "Symbol must be a non-empty string"
        )
    
    symbol = symbol.upper().strip()
    if not symbol.isalpha() or len(symbol) > 10:
        raise APIException(
            ErrorCode.SYMBOL_NOT_FOUND,
            f"Invalid symbol format: {symbol}",
            "Symbol must be 1-10 alphabetic characters"
        )
    
    return symbol


def validate_quantity(quantity: Union[int, float]) -> int:
    """Validate trade quantity"""
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        return quantity
    except (ValueError, TypeError):
        raise APIException(
            ErrorCode.INVALID_PARAMETER,
            "Quantity must be a positive integer"
        )


def validate_strategy(strategy: str) -> str:
    """Validate strategy name"""
    valid_strategies = ['mixed', 'ma_crossover', 'rsi_mean_reversion', 'momentum_breakout', 'test']
    
    if not strategy or strategy not in valid_strategies:
        raise APIException(
            ErrorCode.INVALID_STRATEGY,
            f"Invalid strategy: {strategy}",
            f"Valid strategies: {', '.join(valid_strategies)}"
        )
    
    return strategy


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests = {}
        self.limits = {
            'default': (100, 60),  # 100 requests per 60 seconds
            'trading': (20, 60),   # 20 trading operations per 60 seconds
            'data': (200, 60)      # 200 data requests per 60 seconds
        }
    
    def is_allowed(self, client_id: str, endpoint_type: str = 'default') -> tuple[bool, Dict]:
        """
        Check if request is allowed based on rate limits
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        limit, window = self.limits.get(endpoint_type, self.limits['default'])
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests outside the window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if now - req_time < window
        ]
        
        current_count = len(self.requests[client_id])
        
        rate_info = {
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'reset_time': int(now + window)
        }
        
        if current_count >= limit:
            return False, rate_info
        
        # Add current request
        self.requests[client_id].append(now)
        rate_info['remaining'] = max(0, limit - len(self.requests[client_id]))
        
        return True, rate_info


# Global rate limiter instance
rate_limiter = RateLimiter()