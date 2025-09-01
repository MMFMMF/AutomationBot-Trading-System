"""
Security Management System for AutomationBot Trading Platform

This module provides comprehensive security features including authentication,
authorization, rate limiting, input validation, and security headers.
"""

import os
import time
import hmac
import hashlib
import secrets
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from functools import wraps
from collections import defaultdict, deque
import ipaddress
import re

from core.logging_system import system_monitor
from core.api_response import APIException, ErrorCode


@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    event_type: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    endpoint: str
    timestamp: float
    details: Dict[str, Any]
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    requests_per_window: int
    window_seconds: int
    burst_multiplier: float = 1.5
    enabled: bool = True


@dataclass
class AuthSession:
    """User authentication session"""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: float
    last_activity: float
    expires_at: float
    permissions: List[str]
    is_admin: bool = False


class RateLimiter:
    """
    Advanced rate limiting with different strategies and burst protection
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.client_requests = defaultdict(lambda: deque())
        self.rules = {
            'api_general': RateLimitRule('api_general', 100, 60),
            'api_trading': RateLimitRule('api_trading', 20, 60),
            'api_data': RateLimitRule('api_data', 200, 60),
            'auth': RateLimitRule('auth', 5, 300),  # 5 auth attempts per 5 minutes
            'admin': RateLimitRule('admin', 50, 60),
        }
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('rate_limiter')
    
    def is_allowed(self, client_id: str, rule_name: str = 'api_general') -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limits
        
        Args:
            client_id: Client identifier (IP address, user ID, etc.)
            rule_name: Rate limit rule to apply
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self._lock:
            rule = self.rules.get(rule_name, self.rules['api_general'])
            if not rule.enabled:
                return True, {'rule': rule_name, 'unlimited': True}
            
            current_time = time.time()
            window_start = current_time - rule.window_seconds
            
            # Clean old requests outside the window
            client_queue = self.client_requests[client_id]
            while client_queue and client_queue[0] < window_start:
                client_queue.popleft()
            
            current_count = len(client_queue)
            burst_limit = int(rule.requests_per_window * rule.burst_multiplier)
            
            rate_info = {
                'rule': rule_name,
                'limit': rule.requests_per_window,
                'window_seconds': rule.window_seconds,
                'current_count': current_count,
                'remaining': max(0, rule.requests_per_window - current_count),
                'reset_time': int(current_time + rule.window_seconds),
                'burst_limit': burst_limit
            }
            
            # Check burst protection
            if current_count >= burst_limit:
                self.logger.warning(f"Rate limit exceeded for {client_id}: {current_count}/{burst_limit}")
                return False, rate_info
            
            # Allow request and record it
            client_queue.append(current_time)
            rate_info['remaining'] = max(0, rule.requests_per_window - len(client_queue))
            
            return True, rate_info
    
    def add_custom_rule(self, rule: RateLimitRule) -> None:
        """Add custom rate limiting rule"""
        with self._lock:
            self.rules[rule.name] = rule
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limiting statistics for a client"""
        with self._lock:
            current_time = time.time()
            stats = {}
            
            for rule_name, rule in self.rules.items():
                window_start = current_time - rule.window_seconds
                client_queue = self.client_requests[client_id]
                
                # Count requests in current window
                count = sum(1 for req_time in client_queue if req_time >= window_start)
                
                stats[rule_name] = {
                    'current_count': count,
                    'limit': rule.requests_per_window,
                    'remaining': max(0, rule.requests_per_window - count),
                    'window_seconds': rule.window_seconds
                }
            
            return stats


class InputValidator:
    """
    Comprehensive input validation and sanitization
    """
    
    # Regex patterns for common validations
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    SYMBOL_PATTERN = re.compile(r'^[A-Z]{1,10}$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
    
    # Dangerous patterns to block
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\bunion\b.*\bselect\b)", re.IGNORECASE),
        re.compile(r"(\bdrop\b.*\btable\b)", re.IGNORECASE),
        re.compile(r"(\bdelete\b.*\bfrom\b)", re.IGNORECASE),
        re.compile(r"(\binsert\b.*\binto\b)", re.IGNORECASE),
        re.compile(r"(\bupdate\b.*\bset\b)", re.IGNORECASE),
    ]
    
    XSS_PATTERNS = [
        re.compile(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email address format"""
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_symbol(cls, symbol: str) -> bool:
        """Validate stock symbol format"""
        return bool(cls.SYMBOL_PATTERN.match(symbol))
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format"""
        return bool(cls.UUID_PATTERN.match(uuid_str))
    
    @classmethod
    def check_sql_injection(cls, input_str: str) -> bool:
        """Check for SQL injection patterns"""
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if pattern.search(input_str):
                return True
        return False
    
    @classmethod
    def check_xss(cls, input_str: str) -> bool:
        """Check for XSS patterns"""
        for pattern in cls.XSS_PATTERNS:
            if pattern.search(input_str):
                return True
        return False
    
    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            return str(input_str)[:max_length]
        
        # Check for malicious patterns
        if cls.check_sql_injection(input_str) or cls.check_xss(input_str):
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Input contains potentially malicious content"
            )
        
        # Basic sanitization
        sanitized = input_str.strip()[:max_length]
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        return sanitized
    
    @classmethod
    def validate_ip_address(cls, ip_str: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    @classmethod
    def validate_numeric_range(cls, value: float, min_val: float, max_val: float) -> bool:
        """Validate numeric value is within range"""
        return min_val <= value <= max_val


class SecurityAuditor:
    """
    Security event logging and audit trail
    """
    
    def __init__(self, max_events: int = 10000):
        """Initialize security auditor"""
        self.max_events = max_events
        self.security_events = deque(maxlen=max_events)
        self.threat_scores = defaultdict(float)
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('security_auditor')
    
    def log_event(self, event_type: str, ip_address: str, user_agent: str,
                  endpoint: str, user_id: str = None, risk_level: str = "LOW",
                  **details) -> None:
        """
        Log security event
        
        Args:
            event_type: Type of security event
            ip_address: Client IP address
            user_agent: Client user agent
            endpoint: Endpoint accessed
            user_id: User ID if authenticated
            risk_level: Risk level of event
            **details: Additional event details
        """
        with self._lock:
            event = SecurityEvent(
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                timestamp=time.time(),
                details=details,
                risk_level=risk_level
            )
            
            self.security_events.append(event)
            
            # Update threat score
            self._update_threat_score(ip_address, risk_level)
            
            # Log based on risk level
            if risk_level in ['HIGH', 'CRITICAL']:
                self.logger.error(f"Security event: {event_type}", **details)
            elif risk_level == 'MEDIUM':
                self.logger.warning(f"Security event: {event_type}", **details)
            else:
                self.logger.info(f"Security event: {event_type}", **details)
    
    def _update_threat_score(self, ip_address: str, risk_level: str) -> None:
        """Update threat score for IP address"""
        score_increment = {
            'LOW': 0.1,
            'MEDIUM': 1.0,
            'HIGH': 5.0,
            'CRITICAL': 10.0
        }
        
        self.threat_scores[ip_address] += score_increment.get(risk_level, 0.1)
        
        # Decay threat scores over time
        current_time = time.time()
        if not hasattr(self, '_last_decay') or current_time - self._last_decay > 3600:
            self._decay_threat_scores()
            self._last_decay = current_time
    
    def _decay_threat_scores(self) -> None:
        """Decay threat scores over time"""
        for ip in list(self.threat_scores.keys()):
            self.threat_scores[ip] *= 0.9  # 10% decay
            if self.threat_scores[ip] < 0.01:
                del self.threat_scores[ip]
    
    def get_threat_score(self, ip_address: str) -> float:
        """Get current threat score for IP address"""
        return self.threat_scores.get(ip_address, 0.0)
    
    def is_ip_suspicious(self, ip_address: str, threshold: float = 10.0) -> bool:
        """Check if IP address is suspicious based on threat score"""
        return self.get_threat_score(ip_address) >= threshold
    
    def get_recent_events(self, hours: int = 24, risk_level: str = None) -> List[SecurityEvent]:
        """Get recent security events"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            filtered_events = []
            for event in self.security_events:
                if event.timestamp >= cutoff_time:
                    if risk_level is None or event.risk_level == risk_level:
                        filtered_events.append(event)
            
            return filtered_events


class SecurityManager:
    """
    Main security manager coordinating all security components
    """
    
    def __init__(self):
        """Initialize security manager"""
        self.rate_limiter = RateLimiter()
        self.validator = InputValidator()
        self.auditor = SecurityAuditor()
        self.sessions = {}  # In production, use Redis or database
        self.blocked_ips = set()
        self.admin_ips = set(['127.0.0.1', '::1'])  # Allow localhost admin access
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('security_manager')
        
        # Security configuration
        self.config = {
            'session_timeout': 3600,  # 1 hour
            'max_login_attempts': 5,
            'login_attempt_window': 900,  # 15 minutes
            'auto_block_threshold': 20.0,
            'csrf_protection': True,
            'require_https': False,  # Set to True in production
        }
    
    def authenticate_request(self, request) -> Tuple[bool, Optional[AuthSession]]:
        """
        Authenticate incoming request
        
        Args:
            request: Flask request object
            
        Returns:
            Tuple of (is_authenticated, session_info)
        """
        # Extract session token from headers or cookies
        session_token = request.headers.get('Authorization')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        else:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            return False, None
        
        # Validate session
        session = self.sessions.get(session_token)
        if not session:
            return False, None
        
        # Check session expiration
        if time.time() > session.expires_at:
            self.invalidate_session(session_token)
            return False, None
        
        # Update last activity
        session.last_activity = time.time()
        
        return True, session
    
    def authorize_request(self, session: AuthSession, required_permission: str) -> bool:
        """
        Check if session has required permission
        
        Args:
            session: Authentication session
            required_permission: Required permission string
            
        Returns:
            True if authorized
        """
        if session.is_admin:
            return True
        
        return required_permission in session.permissions
    
    def create_session(self, user_id: str, ip_address: str, user_agent: str,
                      permissions: List[str], is_admin: bool = False) -> str:
        """
        Create new authentication session
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent
            permissions: User permissions
            is_admin: Whether user is admin
            
        Returns:
            Session token
        """
        with self._lock:
            session_token = secrets.token_urlsafe(32)
            current_time = time.time()
            
            session = AuthSession(
                session_id=session_token,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=current_time,
                last_activity=current_time,
                expires_at=current_time + self.config['session_timeout'],
                permissions=permissions,
                is_admin=is_admin
            )
            
            self.sessions[session_token] = session
            
            self.auditor.log_event(
                'session_created',
                ip_address,
                user_agent,
                '/auth/login',
                user_id=user_id,
                risk_level='LOW',
                session_id=session_token
            )
            
            return session_token
    
    def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate authentication session
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            True if session existed and was invalidated
        """
        with self._lock:
            session = self.sessions.pop(session_token, None)
            if session:
                self.auditor.log_event(
                    'session_invalidated',
                    session.ip_address,
                    session.user_agent,
                    '/auth/logout',
                    user_id=session.user_id,
                    risk_level='LOW',
                    session_id=session_token
                )
                return True
            return False
    
    def check_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        if ip_address in self.blocked_ips:
            return True
        
        # Auto-block based on threat score
        if self.auditor.is_ip_suspicious(ip_address, self.config['auto_block_threshold']):
            self.block_ip(ip_address, "Auto-blocked due to suspicious activity")
            return True
        
        return False
    
    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block IP address"""
        with self._lock:
            self.blocked_ips.add(ip_address)
            self.logger.warning(f"IP blocked: {ip_address} - {reason}")
            
            self.auditor.log_event(
                'ip_blocked',
                ip_address,
                'system',
                '/security/block',
                risk_level='HIGH',
                reason=reason
            )
    
    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock IP address"""
        with self._lock:
            if ip_address in self.blocked_ips:
                self.blocked_ips.remove(ip_address)
                self.logger.info(f"IP unblocked: {ip_address}")
                return True
            return False
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        return headers
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get comprehensive security statistics"""
        with self._lock:
            recent_events = self.auditor.get_recent_events(hours=24)
            
            return {
                'blocked_ips': len(self.blocked_ips),
                'active_sessions': len(self.sessions),
                'recent_events': len(recent_events),
                'threat_scores': dict(list(self.auditor.threat_scores.items())[:10]),  # Top 10
                'event_types': {},
                'risk_levels': {},
                'config': self.config
            }


# Global security manager instance
security_manager = SecurityManager()


# Security decorators
def require_auth(permission: str = None):
    """
    Decorator to require authentication for endpoints
    
    Args:
        permission: Required permission (optional)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Check authentication
            is_auth, session = security_manager.authenticate_request(request)
            if not is_auth:
                raise APIException(
                    ErrorCode.UNAUTHORIZED,
                    "Authentication required",
                    http_status=401
                )
            
            # Check authorization
            if permission and not security_manager.authorize_request(session, permission):
                raise APIException(
                    ErrorCode.FORBIDDEN,
                    f"Permission required: {permission}",
                    http_status=403
                )
            
            # Inject session into kwargs
            kwargs['auth_session'] = session
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(rule_name: str = 'api_general'):
    """
    Decorator to apply rate limiting to endpoints
    
    Args:
        rule_name: Rate limit rule to apply
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Get client identifier (IP address or user ID)
            client_id = request.remote_addr
            if hasattr(request, 'auth_session') and request.auth_session:
                client_id = f"user:{request.auth_session.user_id}"
            
            # Check rate limit
            allowed, rate_info = security_manager.rate_limiter.is_allowed(client_id, rule_name)
            
            if not allowed:
                security_manager.auditor.log_event(
                    'rate_limit_exceeded',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    request.endpoint,
                    risk_level='MEDIUM',
                    client_id=client_id,
                    rule=rule_name
                )
                
                raise APIException(
                    ErrorCode.RATE_LIMIT_EXCEEDED,
                    f"Rate limit exceeded: {rate_info['current_count']}/{rate_info['limit']} requests",
                    details=f"Try again in {rate_info['window_seconds']} seconds",
                    http_status=429
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def security_audit(event_type: str, risk_level: str = 'LOW'):
    """
    Decorator to audit endpoint access
    
    Args:
        event_type: Type of security event
        risk_level: Risk level of the event
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            user_id = None
            if hasattr(request, 'auth_session') and request.auth_session:
                user_id = request.auth_session.user_id
            
            security_manager.auditor.log_event(
                event_type,
                request.remote_addr,
                request.headers.get('User-Agent', ''),
                request.endpoint or func.__name__,
                user_id=user_id,
                risk_level=risk_level
            )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator