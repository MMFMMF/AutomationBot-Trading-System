"""
Monitoring and Logging API Routes with Standardized Responses

This module provides API endpoints for system monitoring, logging, and health checks
with proper error handling and structured responses.
"""

from flask import request
from datetime import datetime, timedelta
from core.api_response import (
    APIResponse, APIException, ErrorCode, create_response_decorator
)
from core.logging_system import system_monitor


def register_monitoring_routes(app, logger):
    """
    Register all monitoring and logging routes
    
    Args:
        app: Flask application instance
        logger: Logger instance for route debugging
    """
    
    @app.route('/api/monitoring/health', methods=['GET'])
    @create_response_decorator
    def get_system_health(api_response):
        """Get comprehensive system health status"""
        health_data = system_monitor.run_health_checks()
        
        if health_data['overall_healthy']:
            return api_response.success(health_data, "System health check passed")
        else:
            return api_response.warning(
                health_data,
                "SYSTEM_HEALTH_ISSUES",
                f"{health_data['summary']['failed']} health checks failed",
                "Review failed health checks and address issues"
            )
    
    @app.route('/api/monitoring/metrics', methods=['GET'])
    @create_response_decorator
    def get_system_metrics(api_response):
        """Get comprehensive system metrics and statistics"""
        metrics_data = system_monitor.get_system_metrics()
        return api_response.success(metrics_data, "System metrics retrieved successfully")
    
    @app.route('/api/monitoring/performance', methods=['GET'])
    @create_response_decorator
    def get_performance_metrics(api_response):
        """Get performance metrics with optional filtering"""
        # Parse query parameters
        metric_name = request.args.get('name')
        category = request.args.get('category')
        hours_back = request.args.get('hours', 1, type=int)
        
        if hours_back <= 0 or hours_back > 168:  # Max 1 week
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Hours parameter must be between 1 and 168 (1 week)"
            )
        
        # Calculate time filter
        since_timestamp = (datetime.now() - timedelta(hours=hours_back)).timestamp()
        
        # Get filtered metrics
        metrics = system_monitor.performance_monitor.get_metrics(
            name=metric_name,
            category=category,
            since=since_timestamp
        )
        
        # Get summary statistics
        summary_stats = system_monitor.performance_monitor.get_summary_stats(metric_name)
        
        # Serialize metrics
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                'name': metric.name,
                'value': metric.value,
                'timestamp': datetime.fromtimestamp(metric.timestamp).isoformat(),
                'unit': metric.unit,
                'category': metric.category,
                'tags': metric.tags
            })
        
        response_data = {
            'metrics': metrics_data,
            'summary_stats': summary_stats,
            'filter': {
                'name': metric_name,
                'category': category,
                'hours_back': hours_back
            },
            'count': len(metrics_data)
        }
        
        return api_response.success(response_data, f"Retrieved {len(metrics_data)} performance metrics")
    
    @app.route('/api/monitoring/alerts', methods=['GET'])
    @create_response_decorator
    def get_system_alerts(api_response):
        """Get system alerts with optional filtering"""
        # Parse query parameters
        level = request.args.get('level')
        component = request.args.get('component')
        hours_back = request.args.get('hours', 24, type=int)
        unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
        
        if level and level not in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                f"Invalid alert level: {level}",
                "Valid levels: INFO, WARNING, ERROR, CRITICAL"
            )
        
        if hours_back <= 0 or hours_back > 720:  # Max 30 days
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Hours parameter must be between 1 and 720 (30 days)"
            )
        
        # Calculate time filter
        since_timestamp = (datetime.now() - timedelta(hours=hours_back)).timestamp()
        
        # Get filtered alerts
        alerts = system_monitor.alert_manager.get_alerts(
            level=level,
            component=component,
            since=since_timestamp,
            unresolved_only=unresolved_only
        )
        
        # Serialize alerts
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'level': alert.level,
                'component': alert.component,
                'message': alert.message,
                'timestamp': datetime.fromtimestamp(alert.timestamp).isoformat(),
                'details': alert.details,
                'resolved': alert.resolved
            })
        
        # Group by level for summary
        level_counts = {}
        for alert in alerts:
            level_counts[alert.level] = level_counts.get(alert.level, 0) + 1
        
        response_data = {
            'alerts': alerts_data,
            'summary': {
                'total': len(alerts_data),
                'levels': level_counts,
                'unresolved': len([a for a in alerts if not a.resolved])
            },
            'filter': {
                'level': level,
                'component': component,
                'hours_back': hours_back,
                'unresolved_only': unresolved_only
            }
        }
        
        return api_response.success(response_data, f"Retrieved {len(alerts_data)} system alerts")
    
    @app.route('/api/monitoring/alerts/<int:alert_index>/resolve', methods=['POST'])
    @create_response_decorator
    def resolve_alert(api_response, alert_index):
        """Mark a specific alert as resolved"""
        if alert_index < 0:
            raise APIException(
                ErrorCode.INVALID_PARAMETER,
                "Alert index must be non-negative"
            )
        
        resolved = system_monitor.alert_manager.resolve_alert(alert_index)
        
        if resolved:
            return api_response.success(
                {'alert_index': alert_index, 'resolved': True},
                f"Alert {alert_index} marked as resolved"
            )
        else:
            raise APIException(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Alert with index {alert_index} not found"
            )
    
    @app.route('/api/monitoring/logs', methods=['GET'])
    @create_response_decorator
    def get_log_summary(api_response):
        """Get logging system summary and statistics"""
        # Get basic logger information
        loggers_info = {}
        for name, logger in system_monitor.loggers.items():
            log_file = logger.log_dir / f"{name}.log"
            debug_file = logger.log_dir / f"{name}_debug.log"
            struct_file = logger.log_dir / f"{name}_structured.jsonl"
            
            loggers_info[name] = {
                'log_directory': str(logger.log_dir),
                'files': {
                    'main_log': str(log_file) if log_file.exists() else None,
                    'debug_log': str(debug_file) if debug_file.exists() else None,
                    'structured_log': str(struct_file) if struct_file.exists() else None
                },
                'file_sizes': {
                    'main_log': log_file.stat().st_size if log_file.exists() else 0,
                    'debug_log': debug_file.stat().st_size if debug_file.exists() else 0,
                    'structured_log': struct_file.stat().st_size if struct_file.exists() else 0
                }
            }
        
        response_data = {
            'loggers': loggers_info,
            'summary': {
                'total_loggers': len(system_monitor.loggers),
                'log_directory': 'logging',  # Default directory
                'structured_logging_enabled': True
            }
        }
        
        return api_response.success(response_data, "Logging system summary retrieved successfully")
    
    @app.route('/api/monitoring/performance/clear', methods=['POST'])
    @create_response_decorator
    def clear_performance_metrics(api_response):
        """Clear performance metrics with optional time filtering"""
        data = request.get_json() or {}
        hours_back = data.get('hours_back')
        
        if hours_back is not None:
            if not isinstance(hours_back, (int, float)) or hours_back <= 0:
                raise APIException(
                    ErrorCode.INVALID_PARAMETER,
                    "hours_back must be a positive number"
                )
            
            older_than = (datetime.now() - timedelta(hours=hours_back)).timestamp()
            cleared_count = system_monitor.performance_monitor.clear_metrics(older_than)
        else:
            cleared_count = system_monitor.performance_monitor.clear_metrics()
        
        return api_response.success(
            {'cleared_metrics': cleared_count, 'hours_back': hours_back},
            f"Cleared {cleared_count} performance metrics"
        )
    
    @app.route('/api/monitoring/health-check', methods=['POST'])
    @create_response_decorator
    def register_health_check(api_response):
        """Register a new health check (for development/testing)"""
        data = request.get_json()
        if not data:
            raise APIException(
                ErrorCode.INVALID_REQUEST_FORMAT,
                "Request body must contain health check configuration"
            )
        
        name = data.get('name')
        if not name:
            raise APIException(
                ErrorCode.MISSING_PARAMETER,
                "Health check name is required"
            )
        
        # For demonstration - in real implementation this would register actual checks
        def dummy_health_check():
            return True, {'status': 'OK', 'registered_via': 'API'}
        
        system_monitor.register_health_check(name, dummy_health_check)
        
        return api_response.success(
            {'name': name, 'registered': True},
            f"Health check '{name}' registered successfully"
        )
    
    @app.route('/api/monitoring/system-status', methods=['GET'])
    @create_response_decorator
    def get_system_status_dashboard(api_response):
        """Get comprehensive system status for dashboard display"""
        # Get all monitoring data
        health_data = system_monitor.run_health_checks()
        metrics_data = system_monitor.get_system_metrics()
        
        # Get recent performance summary
        recent_metrics = system_monitor.performance_monitor.get_metrics(
            since=(datetime.now() - timedelta(hours=1)).timestamp()
        )
        
        # Get critical alerts
        critical_alerts = system_monitor.alert_manager.get_alerts(
            level='CRITICAL',
            unresolved_only=True
        )
        
        error_alerts = system_monitor.alert_manager.get_alerts(
            level='ERROR',
            since=(datetime.now() - timedelta(hours=24)).timestamp()
        )
        
        # Build dashboard data
        dashboard_data = {
            'overall_status': 'HEALTHY' if health_data['overall_healthy'] and len(critical_alerts) == 0 else 'DEGRADED',
            'health_summary': {
                'overall_healthy': health_data['overall_healthy'],
                'total_checks': health_data['summary']['total_checks'],
                'passed_checks': health_data['summary']['passed'],
                'failed_checks': health_data['summary']['failed']
            },
            'alerts_summary': {
                'critical_count': len(critical_alerts),
                'error_count_24h': len(error_alerts),
                'total_unresolved': len(system_monitor.alert_manager.get_alerts(unresolved_only=True))
            },
            'performance_summary': {
                'metrics_last_hour': len(recent_metrics),
                'active_loggers': len(system_monitor.loggers),
                'categories_active': list(set(m.category for m in recent_metrics))
            },
            'timestamp': datetime.now().isoformat(),
            'uptime': 'N/A'  # Would be calculated in real implementation
        }
        
        status_message = f"System status: {dashboard_data['overall_status']}"
        if dashboard_data['overall_status'] != 'HEALTHY':
            status_message += f" - {len(critical_alerts)} critical alerts"
        
        return api_response.success(dashboard_data, status_message)