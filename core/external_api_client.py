"""
External API Integration Framework for AutomationBot Trading Platform

This module provides a robust, standardized framework for integrating with
external APIs including retry logic, circuit breakers, rate limiting, and
comprehensive error handling.
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from urllib.parse import urljoin
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.logging_system import system_monitor
from core.performance_optimizer import performance_optimizer
from core.api_response import APIException, ErrorCode


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open (failures)
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class APIEndpoint:
    """External API endpoint configuration"""
    name: str
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    rate_limit: int = 100  # requests per minute
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: int = 60
    headers: Dict[str, str] = field(default_factory=dict)
    auth_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIRequest:
    """API request specification"""
    endpoint: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[float] = None
    cache_ttl: Optional[int] = None


@dataclass
class APIResponse:
    """Standardized API response"""
    success: bool
    status_code: int
    data: Any
    headers: Dict[str, str]
    response_time: float
    cached: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API resilience
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures to open circuit
            recovery_timeout: Time in seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('circuit_breaker')
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            APIException: If circuit is open
        """
        with self._lock:
            current_time = time.time()
            
            # Check if we should attempt recovery
            if (self.state == CircuitState.OPEN and 
                self.last_failure_time and 
                current_time - self.last_failure_time >= self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            
            # Reject calls if circuit is open
            if self.state == CircuitState.OPEN:
                raise APIException(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "Service temporarily unavailable (circuit breaker open)",
                    f"Try again in {self.recovery_timeout - (current_time - self.last_failure_time):.0f} seconds"
                )
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Success - reset failure count and close circuit
                if self.state == CircuitState.HALF_OPEN:
                    self.logger.info("Circuit breaker closing after successful call")
                
                self.failure_count = 0
                self.state = CircuitState.CLOSED
                
                return result
                
            except Exception as e:
                # Failure - increment count and potentially open circuit
                self.failure_count += 1
                self.last_failure_time = current_time
                
                self.logger.warning(f"Circuit breaker recorded failure {self.failure_count}: {e}")
                
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
                
                raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        with self._lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time,
                'recovery_timeout': self.recovery_timeout
            }


class RateLimitManager:
    """
    Rate limiting for external API calls
    """
    
    def __init__(self):
        """Initialize rate limit manager"""
        self.request_times = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, api_name: str, rate_limit: int) -> bool:
        """
        Check if API call is allowed based on rate limit
        
        Args:
            api_name: API identifier
            rate_limit: Requests per minute
            
        Returns:
            True if call is allowed
        """
        with self._lock:
            current_time = time.time()
            minute_ago = current_time - 60
            
            # Initialize or clean old requests
            if api_name not in self.request_times:
                self.request_times[api_name] = []
            
            # Remove requests older than 1 minute
            self.request_times[api_name] = [
                req_time for req_time in self.request_times[api_name]
                if req_time > minute_ago
            ]
            
            # Check rate limit
            if len(self.request_times[api_name]) >= rate_limit:
                return False
            
            # Record this request
            self.request_times[api_name].append(current_time)
            return True
    
    def wait_for_rate_limit(self, api_name: str, rate_limit: int) -> None:
        """
        Wait until rate limit allows request
        
        Args:
            api_name: API identifier
            rate_limit: Requests per minute
        """
        while not self.is_allowed(api_name, rate_limit):
            time.sleep(1)  # Wait 1 second and try again


class ExternalAPIClient:
    """
    Comprehensive external API client with resilience patterns
    """
    
    def __init__(self):
        """Initialize API client"""
        self.endpoints = {}
        self.circuit_breakers = {}
        self.rate_limiters = RateLimitManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AutomationBot-Trading-Platform/2.1',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.logger = system_monitor.get_logger('external_api_client')
        self._lock = threading.RLock()
    
    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        """
        Register an external API endpoint
        
        Args:
            endpoint: API endpoint configuration
        """
        with self._lock:
            self.endpoints[endpoint.name] = endpoint
            self.circuit_breakers[endpoint.name] = CircuitBreaker(
                failure_threshold=endpoint.circuit_failure_threshold,
                recovery_timeout=endpoint.circuit_recovery_timeout
            )
            
            self.logger.info(f"Registered API endpoint: {endpoint.name}")
    
    def _build_url(self, endpoint: APIEndpoint, path: str) -> str:
        """Build complete URL from endpoint and path"""
        return urljoin(endpoint.base_url.rstrip('/') + '/', path.lstrip('/'))
    
    def _prepare_headers(self, endpoint: APIEndpoint, request_headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Prepare request headers"""
        headers = {}
        headers.update(endpoint.headers)
        
        if request_headers:
            headers.update(request_headers)
        
        # Add authentication headers
        auth_config = endpoint.auth_config
        if auth_config.get('type') == 'api_key':
            headers[auth_config['header']] = auth_config['key']
        elif auth_config.get('type') == 'bearer':
            headers['Authorization'] = f"Bearer {auth_config['token']}"
        
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    )
    def _make_request(self, endpoint: APIEndpoint, api_request: APIRequest) -> APIResponse:
        """
        Make HTTP request with retry logic
        
        Args:
            endpoint: API endpoint configuration
            api_request: Request specification
            
        Returns:
            API response
        """
        # Build request parameters
        url = self._build_url(endpoint, api_request.endpoint)
        headers = self._prepare_headers(endpoint, api_request.headers)
        timeout = api_request.timeout or endpoint.timeout
        
        # Start timing
        start_time = time.time()
        
        try:
            # Make the request
            response = self.session.request(
                method=api_request.method,
                url=url,
                params=api_request.params,
                json=api_request.data if api_request.method in ['POST', 'PUT', 'PATCH'] else None,
                headers=headers,
                timeout=timeout
            )
            
            response_time = time.time() - start_time
            
            # Parse response data
            try:
                data = response.json()
            except ValueError:
                data = response.text
            
            # Create response object
            api_response = APIResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                response_time=response_time
            )
            
            # Log successful request
            self.logger.info(
                f"API request successful: {endpoint.name} {api_request.method} {api_request.endpoint}",
                status_code=response.status_code,
                response_time=response_time
            )
            
            # Record performance metric
            performance_optimizer.performance_monitor.record_metric(
                f"external_api.{endpoint.name}",
                response_time * 1000,  # Convert to milliseconds
                unit="ms",
                category="external_api"
            )
            
            return api_response
            
        except requests.exceptions.Timeout as e:
            response_time = time.time() - start_time
            self.logger.error(f"API request timeout: {endpoint.name} {api_request.endpoint}")
            
            raise APIException(
                ErrorCode.PROVIDER_UNAVAILABLE,
                f"Request to {endpoint.name} timed out after {timeout}s",
                str(e)
            )
            
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            self.logger.error(f"API connection error: {endpoint.name} {api_request.endpoint}")
            
            raise APIException(
                ErrorCode.PROVIDER_UNAVAILABLE,
                f"Cannot connect to {endpoint.name}",
                str(e)
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error(f"API request error: {endpoint.name} {api_request.endpoint}: {e}")
            
            raise APIException(
                ErrorCode.INTERNAL_ERROR,
                f"API request failed: {endpoint.name}",
                str(e)
            )
    
    def call_api(self, endpoint_name: str, request: APIRequest) -> APIResponse:
        """
        Make API call with full resilience patterns
        
        Args:
            endpoint_name: Name of registered endpoint
            request: API request specification
            
        Returns:
            API response
        """
        # Get endpoint configuration
        if endpoint_name not in self.endpoints:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                f"Unknown API endpoint: {endpoint_name}",
                f"Available endpoints: {', '.join(self.endpoints.keys())}"
            )
        
        endpoint = self.endpoints[endpoint_name]
        circuit_breaker = self.circuit_breakers[endpoint_name]
        
        # Check cache first if TTL specified
        cache_key = None
        if request.cache_ttl and request.method == 'GET':
            cache_key = f"api:{endpoint_name}:{hashlib.md5(str(request.__dict__).encode()).hexdigest()}"
            cached_response = performance_optimizer.cache.get(cache_key)
            
            if cached_response:
                cached_response.cached = True
                self.logger.debug(f"API response served from cache: {endpoint_name}")
                return cached_response
        
        # Rate limiting
        if not self.rate_limiters.is_allowed(endpoint_name, endpoint.rate_limit):
            self.logger.warning(f"Rate limit exceeded for {endpoint_name}, waiting...")
            self.rate_limiters.wait_for_rate_limit(endpoint_name, endpoint.rate_limit)
        
        # Make request through circuit breaker
        def make_request():
            return self._make_request(endpoint, request)
        
        try:
            response = circuit_breaker.call(make_request)
            
            # Cache successful GET responses
            if (request.cache_ttl and request.method == 'GET' and 
                response.success and cache_key):
                performance_optimizer.cache.set(cache_key, response, ttl=request.cache_ttl)
            
            return response
            
        except Exception as e:
            # Log the error
            self.logger.error(f"API call failed: {endpoint_name} - {str(e)}")
            raise
    
    def get_endpoint_status(self, endpoint_name: str = None) -> Dict[str, Any]:
        """
        Get status of endpoints and circuit breakers
        
        Args:
            endpoint_name: Specific endpoint name, or None for all
            
        Returns:
            Status information
        """
        with self._lock:
            if endpoint_name:
                if endpoint_name not in self.endpoints:
                    raise APIException(
                        ErrorCode.RESOURCE_NOT_FOUND,
                        f"Endpoint {endpoint_name} not found"
                    )
                
                return {
                    endpoint_name: {
                        'circuit_breaker': self.circuit_breakers[endpoint_name].get_status(),
                        'endpoint_config': {
                            'base_url': self.endpoints[endpoint_name].base_url,
                            'rate_limit': self.endpoints[endpoint_name].rate_limit,
                            'timeout': self.endpoints[endpoint_name].timeout
                        }
                    }
                }
            else:
                status = {}
                for name in self.endpoints:
                    status[name] = {
                        'circuit_breaker': self.circuit_breakers[name].get_status(),
                        'endpoint_config': {
                            'base_url': self.endpoints[name].base_url,
                            'rate_limit': self.endpoints[name].rate_limit,
                            'timeout': self.endpoints[name].timeout
                        }
                    }
                
                return status


# Global API client instance
api_client = ExternalAPIClient()


# Convenience functions for common API patterns
def register_polygon_api(api_key: str) -> None:
    """Register Polygon.io API endpoint"""
    endpoint = APIEndpoint(
        name="polygon",
        base_url="https://api.polygon.io",
        timeout=30.0,
        max_retries=3,
        rate_limit=100,  # requests per minute
        circuit_failure_threshold=5,
        circuit_recovery_timeout=60,
        auth_config={
            'type': 'api_key',
            'header': 'Authorization',
            'key': f'Bearer {api_key}'
        }
    )
    api_client.register_endpoint(endpoint)


def register_alpaca_api(api_key: str, secret_key: str, paper: bool = True) -> None:
    """Register Alpaca API endpoint"""
    base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
    
    endpoint = APIEndpoint(
        name="alpaca",
        base_url=base_url,
        timeout=30.0,
        max_retries=3,
        rate_limit=200,  # requests per minute
        circuit_failure_threshold=5,
        circuit_recovery_timeout=60,
        headers={
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': secret_key
        }
    )
    api_client.register_endpoint(endpoint)


def register_alpha_vantage_api(api_key: str) -> None:
    """Register Alpha Vantage API endpoint"""
    endpoint = APIEndpoint(
        name="alpha_vantage",
        base_url="https://www.alphavantage.co",
        timeout=30.0,
        max_retries=3,
        rate_limit=5,  # Very limited free tier
        circuit_failure_threshold=3,
        circuit_recovery_timeout=300,  # 5 minutes
        headers={
            'User-Agent': 'AutomationBot-Trading-Platform/2.1'
        }
    )
    api_client.register_endpoint(endpoint)