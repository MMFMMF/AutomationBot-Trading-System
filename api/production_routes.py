"""
Production-Ready API Routes with Performance, Security, and Monitoring

This module provides production-grade API endpoints with comprehensive
security, performance optimization, and monitoring capabilities.
"""

from flask import request, make_response
from datetime import datetime
from core.api_response import (
    APIResponse, APIException, ErrorCode, create_response_decorator
)
from core.performance_optimizer import performance_optimizer, cached_endpoint, monitor_performance
from core.security_manager import security_manager, require_auth, rate_limit, security_audit
from core.logging_system import system_monitor


def register_production_routes(app, logger):
    """
    Register all production monitoring and management routes
    
    Args:
        app: Flask application instance
        logger: Logger instance for route debugging
    """
    
    @app.before_request
    def security_check():
        """Security checks before processing any request"""
        client_ip = request.remote_addr
        
        # Check if IP is blocked
        if security_manager.check_ip_blocked(client_ip):
            security_manager.auditor.log_event(
                'blocked_ip_access_attempt',
                client_ip,
                request.headers.get('User-Agent', ''),
                request.endpoint or '',
                risk_level='HIGH'
            )
            
            raise APIException(
                ErrorCode.FORBIDDEN,
                "Access denied",
                http_status=403
            )
        
        # Input validation for all requests
        if request.content_length and request.content_length > 1024 * 1024:  # 1MB limit
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Request payload too large",
                http_status=413
            )
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        headers = security_manager.get_security_headers()
        for header, value in headers.items():
            response.headers[header] = value
        return response
    
    # Performance Monitoring Routes
    @app.route('/api/admin/performance', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('performance_stats_access', 'LOW')
    @monitor_performance('get_performance_stats')
    def get_performance_stats(api_response, auth_session):
        """Get comprehensive performance statistics"""
        stats = performance_optimizer.get_comprehensive_stats()
        
        # Add system monitor stats
        system_stats = system_monitor.get_system_metrics()
        stats['system_monitor'] = system_stats
        
        return api_response.success(stats, "Performance statistics retrieved successfully")
    
    @app.route('/api/admin/performance/cache/clear', methods=['POST'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('cache_clear', 'MEDIUM')
    @monitor_performance('clear_cache')
    def clear_performance_cache(api_response, auth_session):
        """Clear all performance caches"""
        clear_stats = performance_optimizer.clear_all_caches()
        
        logger.info(f"Admin {auth_session.user_id} cleared performance cache")
        
        return api_response.success(clear_stats, "Performance cache cleared successfully")
    
    @app.route('/api/admin/performance/endpoints', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @cached_endpoint(ttl=60)  # Cache for 1 minute
    def get_endpoint_performance(api_response, auth_session):
        """Get endpoint performance statistics"""
        endpoint_stats = dict(performance_optimizer.endpoint_stats)
        
        # Sort by average response time
        sorted_endpoints = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1].get('avg_time', 0),
            reverse=True
        )
        
        performance_data = {
            'total_endpoints': len(endpoint_stats),
            'slowest_endpoints': sorted_endpoints[:10],
            'total_requests': sum(stats.get('count', 0) for stats in endpoint_stats.values()),
            'total_errors': sum(stats.get('errors', 0) for stats in endpoint_stats.values()),
        }
        
        return api_response.success(performance_data, "Endpoint performance statistics retrieved")
    
    # Security Management Routes
    @app.route('/api/admin/security', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('security_stats_access', 'LOW')
    @monitor_performance('get_security_stats')
    def get_security_stats(api_response, auth_session):
        """Get comprehensive security statistics"""
        stats = security_manager.get_security_stats()
        
        # Add recent security events
        recent_events = security_manager.auditor.get_recent_events(hours=24)
        stats['recent_events_count'] = len(recent_events)
        
        # Group events by type and risk level
        event_types = {}
        risk_levels = {}
        
        for event in recent_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            risk_levels[event.risk_level] = risk_levels.get(event.risk_level, 0) + 1
        
        stats['event_types'] = event_types
        stats['risk_levels'] = risk_levels
        
        return api_response.success(stats, "Security statistics retrieved successfully")
    
    @app.route('/api/admin/security/events', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('security_events_access', 'MEDIUM')
    def get_security_events(api_response, auth_session):
        """Get recent security events"""
        hours = request.args.get('hours', 24, type=int)
        risk_level = request.args.get('risk_level')
        
        if hours <= 0 or hours > 168:  # Max 1 week
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Hours parameter must be between 1 and 168"
            )
        
        events = security_manager.auditor.get_recent_events(hours, risk_level)
        
        # Serialize events
        events_data = []
        for event in events:
            events_data.append({
                'event_type': event.event_type,
                'user_id': event.user_id,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'endpoint': event.endpoint,
                'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
                'risk_level': event.risk_level,
                'details': event.details
            })
        
        return api_response.success(
            {
                'events': events_data,
                'total_count': len(events_data),
                'filter': {'hours': hours, 'risk_level': risk_level}
            },
            f"Retrieved {len(events_data)} security events"
        )
    
    @app.route('/api/admin/security/block-ip', methods=['POST'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('manual_ip_block', 'HIGH')
    def block_ip_address(api_response, auth_session):
        """Manually block IP address"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body required"
            )
        
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'Manually blocked by admin')
        
        if not ip_address:
            raise APIException(
                ErrorCode.MISSING_PARAMETER,
                "ip_address is required"
            )
        
        # Validate IP address format
        from core.security_manager import InputValidator
        if not InputValidator.validate_ip_address(ip_address):
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Invalid IP address format"
            )
        
        # Don't allow blocking admin IPs
        if ip_address in security_manager.admin_ips:
            raise APIException(
                ErrorCode.FORBIDDEN,
                "Cannot block admin IP address"
            )
        
        security_manager.block_ip(ip_address, f"{reason} (by admin {auth_session.user_id})")
        
        return api_response.success(
            {'ip_address': ip_address, 'blocked': True, 'reason': reason},
            f"IP address {ip_address} blocked successfully"
        )
    
    @app.route('/api/admin/security/unblock-ip', methods=['POST'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('manual_ip_unblock', 'MEDIUM')
    def unblock_ip_address(api_response, auth_session):
        """Manually unblock IP address"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body required"
            )
        
        ip_address = data.get('ip_address')
        
        if not ip_address:
            raise APIException(
                ErrorCode.MISSING_PARAMETER,
                "ip_address is required"
            )
        
        success = security_manager.unblock_ip(ip_address)
        
        if success:
            return api_response.success(
                {'ip_address': ip_address, 'unblocked': True},
                f"IP address {ip_address} unblocked successfully"
            )
        else:
            raise APIException(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"IP address {ip_address} was not blocked"
            )
    
    @app.route('/api/admin/security/sessions', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('session_list_access', 'LOW')
    def get_active_sessions(api_response, auth_session):
        """Get list of active sessions"""
        sessions_data = []
        
        for session_id, session in security_manager.sessions.items():
            sessions_data.append({
                'session_id': session_id[:8] + '...',  # Partial ID for security
                'user_id': session.user_id,
                'ip_address': session.ip_address,
                'created_at': datetime.fromtimestamp(session.created_at).isoformat(),
                'last_activity': datetime.fromtimestamp(session.last_activity).isoformat(),
                'expires_at': datetime.fromtimestamp(session.expires_at).isoformat(),
                'is_admin': session.is_admin,
                'permissions': session.permissions
            })
        
        return api_response.success(
            {
                'sessions': sessions_data,
                'total_count': len(sessions_data)
            },
            f"Retrieved {len(sessions_data)} active sessions"
        )
    
    # System Health and Monitoring Routes
    @app.route('/api/admin/system/health', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @cached_endpoint(ttl=30)  # Cache for 30 seconds
    def get_system_health(api_response, auth_session):
        """Get comprehensive system health status"""
        # Get health data from system monitor
        health_data = system_monitor.run_health_checks()
        
        # Add performance metrics
        perf_stats = performance_optimizer.get_comprehensive_stats()
        health_data['performance'] = {
            'cache_hit_rate': perf_stats['cache'].get('hit_rate', 0),
            'database_connections': perf_stats['database_pool'],
            'memory_usage': perf_stats['cache'].get('memory_usage_percent', 0)
        }
        
        # Add security status
        security_stats = security_manager.get_security_stats()
        health_data['security'] = {
            'blocked_ips': security_stats['blocked_ips'],
            'active_sessions': security_stats['active_sessions'],
            'recent_threats': len([
                event for event in security_manager.auditor.get_recent_events(1)
                if event.risk_level in ['HIGH', 'CRITICAL']
            ])
        }
        
        # Determine overall health status
        overall_status = 'HEALTHY'
        if not health_data['overall_healthy']:
            overall_status = 'DEGRADED'
        if health_data['security']['recent_threats'] > 5:
            overall_status = 'AT_RISK'
        
        health_data['system_status'] = overall_status
        
        return api_response.success(health_data, f"System health status: {overall_status}")
    
    @app.route('/api/admin/system/metrics/export', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('metrics_export', 'LOW')
    @monitor_performance('export_metrics')
    def export_system_metrics(api_response, auth_session):
        """Export comprehensive system metrics"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'performance': performance_optimizer.get_comprehensive_stats(),
            'security': security_manager.get_security_stats(),
            'monitoring': system_monitor.get_system_metrics(),
            'metadata': {
                'exported_by': auth_session.user_id,
                'export_type': 'full_system_metrics',
                'version': '2.1'
            }
        }
        
        # Add recent security events for audit trail
        recent_events = security_manager.auditor.get_recent_events(hours=24)
        export_data['security']['recent_events'] = [
            {
                'event_type': event.event_type,
                'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
                'risk_level': event.risk_level,
                'ip_address': event.ip_address,
                'endpoint': event.endpoint
            }
            for event in recent_events[-100:]  # Last 100 events
        ]
        
        return api_response.success(export_data, "System metrics exported successfully")
    
    # Database and Storage Management
    @app.route('/api/admin/database/stats', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @cached_endpoint(ttl=120)  # Cache for 2 minutes
    def get_database_stats(api_response, auth_session):
        """Get database performance statistics"""
        db_stats = performance_optimizer.connection_pool.get_stats()
        query_stats = performance_optimizer.query_optimizer.get_query_stats()
        
        # Get top 10 slowest queries
        slowest_queries = sorted(
            query_stats.items(),
            key=lambda x: x[1].get('avg_time', 0),
            reverse=True
        )[:10]
        
        database_data = {
            'connection_pool': db_stats,
            'query_performance': {
                'total_queries': len(query_stats),
                'slowest_queries': [
                    {
                        'query': query[:100] + '...' if len(query) > 100 else query,
                        'avg_time': stats['avg_time'],
                        'total_time': stats['total_time'],
                        'count': stats['count']
                    }
                    for query, stats in slowest_queries
                ]
            }
        }
        
        return api_response.success(database_data, "Database statistics retrieved successfully")
    
    # Configuration Management
    @app.route('/api/admin/config/security', methods=['GET'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    def get_security_config(api_response, auth_session):
        """Get current security configuration"""
        config = security_manager.config.copy()
        
        # Don't expose sensitive configuration details
        safe_config = {
            'session_timeout': config['session_timeout'],
            'max_login_attempts': config['max_login_attempts'],
            'login_attempt_window': config['login_attempt_window'],
            'auto_block_threshold': config['auto_block_threshold'],
            'csrf_protection': config['csrf_protection'],
            'require_https': config['require_https']
        }
        
        return api_response.success(safe_config, "Security configuration retrieved successfully")
    
    @app.route('/api/admin/config/security', methods=['PUT'])
    @create_response_decorator
    @require_auth('admin')
    @rate_limit('admin')
    @security_audit('security_config_update', 'HIGH')
    def update_security_config(api_response, auth_session):
        """Update security configuration"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body required"
            )
        
        # Validate configuration updates
        allowed_updates = [
            'session_timeout', 'max_login_attempts', 'login_attempt_window',
            'auto_block_threshold', 'csrf_protection', 'require_https'
        ]
        
        updates = {}
        for key, value in data.items():
            if key not in allowed_updates:
                raise APIException(
                    ErrorCode.INVALID_PARAMETER,
                    f"Configuration key '{key}' is not allowed"
                )
            
            # Basic validation
            if key in ['session_timeout', 'max_login_attempts', 'login_attempt_window']:
                if not isinstance(value, int) or value <= 0:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        f"'{key}' must be a positive integer"
                    )
            elif key == 'auto_block_threshold':
                if not isinstance(value, (int, float)) or value <= 0:
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        f"'{key}' must be a positive number"
                    )
            elif key in ['csrf_protection', 'require_https']:
                if not isinstance(value, bool):
                    raise APIException(
                        ErrorCode.INVALID_PARAMETER,
                        f"'{key}' must be a boolean"
                    )
            
            updates[key] = value
        
        # Apply updates
        security_manager.config.update(updates)
        
        logger.info(f"Security configuration updated by admin {auth_session.user_id}: {updates}")
        
        return api_response.success(
            {'updated_config': updates, 'updated_by': auth_session.user_id},
            f"Security configuration updated successfully"
        )