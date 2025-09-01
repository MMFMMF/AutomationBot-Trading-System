"""
Comprehensive Logging and Monitoring System for AutomationBot Trading Platform

This module provides unified logging, performance monitoring, and system health
tracking across all platform components.
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import traceback


@dataclass
class PerformanceMetric:
    """Performance tracking data point"""
    name: str
    value: float
    timestamp: float
    unit: str = "ms"
    category: str = "general"
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class SystemAlert:
    """System alert/notification"""
    level: str  # INFO, WARNING, ERROR, CRITICAL
    component: str
    message: str
    timestamp: float
    details: Dict[str, Any] = None
    resolved: bool = False
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class PerformanceMonitor:
    """
    System-wide performance monitoring and metrics collection
    """
    
    def __init__(self, max_metrics: int = 10000):
        """
        Initialize performance monitor
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.max_metrics = max_metrics
        self.metrics = deque(maxlen=max_metrics)
        self.metric_summaries = defaultdict(lambda: {
            'count': 0, 'total': 0.0, 'min': float('inf'), 'max': 0.0, 'avg': 0.0
        })
        self._lock = threading.RLock()
    
    def record_metric(self, name: str, value: float, unit: str = "ms", 
                     category: str = "general", **tags) -> None:
        """
        Record a performance metric
        
        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            category: Metric category
            **tags: Additional tags for the metric
        """
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=time.time(),
                unit=unit,
                category=category,
                tags=tags
            )
            
            self.metrics.append(metric)
            
            # Update summary statistics
            summary = self.metric_summaries[name]
            summary['count'] += 1
            summary['total'] += value
            summary['min'] = min(summary['min'], value)
            summary['max'] = max(summary['max'], value)
            summary['avg'] = summary['total'] / summary['count']
    
    def get_metrics(self, name: str = None, category: str = None, 
                   since: float = None) -> List[PerformanceMetric]:
        """
        Retrieve metrics with optional filtering
        
        Args:
            name: Filter by metric name
            category: Filter by category
            since: Filter by timestamp (Unix timestamp)
            
        Returns:
            List of matching metrics
        """
        with self._lock:
            filtered_metrics = []
            for metric in self.metrics:
                if name and metric.name != name:
                    continue
                if category and metric.category != category:
                    continue
                if since and metric.timestamp < since:
                    continue
                filtered_metrics.append(metric)
            return filtered_metrics
    
    def get_summary_stats(self, name: str = None) -> Dict[str, Any]:
        """
        Get summary statistics for metrics
        
        Args:
            name: Specific metric name, or None for all
            
        Returns:
            Dictionary of summary statistics
        """
        with self._lock:
            if name:
                return {name: dict(self.metric_summaries[name])}
            else:
                return {k: dict(v) for k, v in self.metric_summaries.items()}
    
    def clear_metrics(self, older_than: float = None) -> int:
        """
        Clear metrics, optionally only those older than specified time
        
        Args:
            older_than: Unix timestamp - clear metrics older than this
            
        Returns:
            Number of metrics cleared
        """
        with self._lock:
            if older_than is None:
                count = len(self.metrics)
                self.metrics.clear()
                self.metric_summaries.clear()
                return count
            else:
                # Filter out old metrics
                original_count = len(self.metrics)
                self.metrics = deque(
                    [m for m in self.metrics if m.timestamp >= older_than],
                    maxlen=self.max_metrics
                )
                return original_count - len(self.metrics)


class AlertManager:
    """
    System alert and notification management
    """
    
    def __init__(self, max_alerts: int = 1000):
        """
        Initialize alert manager
        
        Args:
            max_alerts: Maximum number of alerts to keep in memory
        """
        self.max_alerts = max_alerts
        self.alerts = deque(maxlen=max_alerts)
        self.alert_handlers = defaultdict(list)
        self._lock = threading.RLock()
    
    def create_alert(self, level: str, component: str, message: str, 
                    **details) -> SystemAlert:
        """
        Create and register a system alert
        
        Args:
            level: Alert level (INFO, WARNING, ERROR, CRITICAL)
            component: Component that generated the alert
            message: Alert message
            **details: Additional alert details
            
        Returns:
            Created alert
        """
        with self._lock:
            alert = SystemAlert(
                level=level,
                component=component,
                message=message,
                timestamp=time.time(),
                details=details
            )
            
            self.alerts.append(alert)
            
            # Notify handlers
            for handler in self.alert_handlers[level]:
                try:
                    handler(alert)
                except Exception as e:
                    print(f"Error in alert handler: {e}")
            
            return alert
    
    def get_alerts(self, level: str = None, component: str = None,
                  since: float = None, unresolved_only: bool = False) -> List[SystemAlert]:
        """
        Retrieve alerts with optional filtering
        
        Args:
            level: Filter by alert level
            component: Filter by component
            since: Filter by timestamp
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of matching alerts
        """
        with self._lock:
            filtered_alerts = []
            for alert in self.alerts:
                if level and alert.level != level:
                    continue
                if component and alert.component != component:
                    continue
                if since and alert.timestamp < since:
                    continue
                if unresolved_only and alert.resolved:
                    continue
                filtered_alerts.append(alert)
            return filtered_alerts
    
    def resolve_alert(self, alert_index: int) -> bool:
        """
        Mark an alert as resolved
        
        Args:
            alert_index: Index of alert to resolve
            
        Returns:
            True if alert was found and resolved
        """
        with self._lock:
            try:
                self.alerts[alert_index].resolved = True
                return True
            except IndexError:
                return False
    
    def register_alert_handler(self, level: str, handler: Callable) -> None:
        """
        Register a handler for alerts of specific level
        
        Args:
            level: Alert level to handle
            handler: Function to call when alert is created
        """
        self.alert_handlers[level].append(handler)


class StructuredLogger:
    """
    Enhanced logging with structured data and performance tracking
    """
    
    def __init__(self, name: str, log_dir: str = "logging", 
                 performance_monitor: PerformanceMonitor = None):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            performance_monitor: Performance monitor instance
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.performance_monitor = performance_monitor
        
        # Set up standard logger
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up logging handlers"""
        self.logger.setLevel(logging.DEBUG)
        
        # File handler for general logs
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # File handler for debug logs
        debug_file = self.log_dir / f"{self.name}_debug.log"
        debug_handler = logging.FileHandler(debug_file)
        debug_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        debug_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(debug_handler)
        self.logger.addHandler(console_handler)
    
    def log_with_context(self, level: str, message: str, **context):
        """
        Log message with structured context data
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **context: Additional context data
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'component': self.name,
            'message': message,
            'context': context
        }
        
        # Add structured data to message
        if context:
            context_str = json.dumps(context, indent=None, separators=(',', ':'))
            full_message = f"{message} | Context: {context_str}"
        else:
            full_message = message
        
        # Log using standard logger
        getattr(self.logger, level.lower())(full_message)
        
        # Write structured log to separate file
        struct_file = self.log_dir / f"{self.name}_structured.jsonl"
        try:
            with open(struct_file, 'a') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write structured log: {e}")
    
    def log_performance(self, operation: str, duration: float, **context):
        """
        Log performance data
        
        Args:
            operation: Operation name
            duration: Operation duration in milliseconds
            **context: Additional context
        """
        if self.performance_monitor:
            self.performance_monitor.record_metric(
                name=f"{self.name}.{operation}",
                value=duration,
                unit="ms",
                category="performance",
                component=self.name,
                **context
            )
        
        self.log_with_context(
            'info',
            f"Performance: {operation} took {duration:.2f}ms",
            operation=operation,
            duration=duration,
            **context
        )
    
    def debug(self, message: str, **context):
        """Log debug message with context"""
        self.log_with_context('debug', message, **context)
    
    def info(self, message: str, **context):
        """Log info message with context"""
        self.log_with_context('info', message, **context)
    
    def warning(self, message: str, **context):
        """Log warning message with context"""
        self.log_with_context('warning', message, **context)
    
    def error(self, message: str, **context):
        """Log error message with context"""
        if 'traceback' not in context:
            context['traceback'] = traceback.format_exc()
        self.log_with_context('error', message, **context)
    
    def critical(self, message: str, **context):
        """Log critical message with context"""
        if 'traceback' not in context:
            context['traceback'] = traceback.format_exc()
        self.log_with_context('critical', message, **context)


class SystemMonitor:
    """
    Comprehensive system monitoring and health tracking
    """
    
    def __init__(self):
        """Initialize system monitor"""
        self.performance_monitor = PerformanceMonitor()
        self.alert_manager = AlertManager()
        self.loggers = {}
        self.health_checks = {}
        self._lock = threading.RLock()
    
    def get_logger(self, name: str) -> StructuredLogger:
        """
        Get or create a structured logger
        
        Args:
            name: Logger name
            
        Returns:
            StructuredLogger instance
        """
        with self._lock:
            if name not in self.loggers:
                self.loggers[name] = StructuredLogger(
                    name, 
                    performance_monitor=self.performance_monitor
                )
            return self.loggers[name]
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function
        
        Args:
            name: Health check name
            check_func: Function that returns (healthy: bool, details: dict)
        """
        self.health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Any]:
        """
        Run all registered health checks
        
        Returns:
            Dictionary of health check results
        """
        results = {}
        overall_healthy = True
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                healthy, details = check_func()
                duration = (time.time() - start_time) * 1000
                
                results[name] = {
                    'healthy': healthy,
                    'details': details,
                    'check_duration_ms': duration,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                if not healthy:
                    overall_healthy = False
                    self.alert_manager.create_alert(
                        'WARNING',
                        'SystemMonitor',
                        f"Health check failed: {name}",
                        check_name=name,
                        details=details
                    )
                
            except Exception as e:
                overall_healthy = False
                results[name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                self.alert_manager.create_alert(
                    'ERROR',
                    'SystemMonitor',
                    f"Health check error: {name}",
                    check_name=name,
                    error=str(e),
                    traceback=traceback.format_exc()
                )
        
        return {
            'overall_healthy': overall_healthy,
            'checks': results,
            'summary': {
                'total_checks': len(self.health_checks),
                'passed': sum(1 for r in results.values() if r.get('healthy', False)),
                'failed': sum(1 for r in results.values() if not r.get('healthy', True))
            }
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics
        
        Returns:
            Dictionary of system metrics and status
        """
        current_time = time.time()
        last_hour = current_time - 3600
        
        # Performance metrics summary
        perf_stats = self.performance_monitor.get_summary_stats()
        recent_metrics = self.performance_monitor.get_metrics(since=last_hour)
        
        # Alert summary
        recent_alerts = self.alert_manager.get_alerts(since=last_hour)
        unresolved_alerts = self.alert_manager.get_alerts(unresolved_only=True)
        
        # Health check status
        health_status = self.run_health_checks()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance': {
                'summary_stats': perf_stats,
                'recent_metrics_count': len(recent_metrics),
                'categories': list(set(m.category for m in recent_metrics))
            },
            'alerts': {
                'recent_count': len(recent_alerts),
                'unresolved_count': len(unresolved_alerts),
                'levels': {
                    level: len([a for a in recent_alerts if a.level == level])
                    for level in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
                }
            },
            'health': health_status,
            'system': {
                'loggers_active': len(self.loggers),
                'health_checks_registered': len(self.health_checks),
                'uptime': 'N/A'  # This would be calculated in real implementation
            }
        }


# Global system monitor instance
system_monitor = SystemMonitor()


# Decorators for automatic performance and error logging
def log_performance(operation_name: str = None):
    """
    Decorator to automatically log function performance
    
    Args:
        operation_name: Custom operation name (defaults to function name)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            logger = system_monitor.get_logger(func.__module__ or 'default')
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.log_performance(name, duration)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Error in {name}: {str(e)}",
                    operation=name,
                    duration=duration,
                    error_type=type(e).__name__
                )
                raise
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def log_errors(component: str = None):
    """
    Decorator to automatically log function errors
    
    Args:
        component: Component name for logging context
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            comp_name = component or func.__module__ or 'default'
            logger = system_monitor.get_logger(comp_name)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                
                # Create system alert for critical errors
                if isinstance(e, (SystemError, MemoryError, OSError)):
                    system_monitor.alert_manager.create_alert(
                        'CRITICAL',
                        comp_name,
                        f"Critical error in {func.__name__}: {str(e)}",
                        function=func.__name__,
                        error_type=type(e).__name__
                    )
                
                raise
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator