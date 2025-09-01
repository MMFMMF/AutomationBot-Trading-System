"""
Performance Optimization and Caching System for AutomationBot Trading Platform

This module provides comprehensive performance optimization including caching,
database connection pooling, query optimization, and response compression.
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps, lru_cache
from dataclasses import dataclass
from collections import defaultdict, OrderedDict, deque
import sqlite3
import gzip
import pickle

from core.logging_system import system_monitor


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = None
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at


class InMemoryCache:
    """
    High-performance in-memory cache with TTL, LRU eviction, and size limits
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.stats = {
            'hits': 0, 'misses': 0, 'evictions': 0,
            'size_bytes': 0, 'max_size_bytes': 100 * 1024 * 1024  # 100MB
        }
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('cache')
    
    def _generate_key(self, key: Union[str, tuple]) -> str:
        """Generate cache key from various inputs"""
        if isinstance(key, str):
            return key
        elif isinstance(key, (tuple, list)):
            return hashlib.md5(str(key).encode()).hexdigest()
        else:
            return hashlib.md5(str(key).encode()).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of cached value"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode())
    
    def _evict_expired(self) -> int:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.expires_at and current_time > entry.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
        
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Remove least recently used entries if over size limit"""
        while len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self._remove_entry(oldest_key)
            self.stats['evictions'] += 1
    
    def _remove_entry(self, key: str) -> None:
        """Remove cache entry and update stats"""
        if key in self.cache:
            entry = self.cache[key]
            self.stats['size_bytes'] -= entry.size_bytes
            del self.cache[key]
    
    def get(self, key: Union[str, tuple], default: Any = None) -> Any:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            cache_key = self._generate_key(key)
            
            # Clean expired entries periodically
            if len(self.cache) % 100 == 0:
                self._evict_expired()
            
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                # Check if expired
                if entry.expires_at and time.time() > entry.expires_at:
                    self._remove_entry(cache_key)
                    self.stats['misses'] += 1
                    return default
                
                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = time.time()
                
                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                
                self.stats['hits'] += 1
                return entry.value
            else:
                self.stats['misses'] += 1
                return default
    
    def set(self, key: Union[str, tuple], value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for default)
        """
        with self._lock:
            cache_key = self._generate_key(key)
            
            # Calculate expiration time
            current_time = time.time()
            expires_at = None
            if ttl is not None:
                expires_at = current_time + ttl
            elif self.default_ttl > 0:
                expires_at = current_time + self.default_ttl
            
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Remove old entry if exists
            if cache_key in self.cache:
                self._remove_entry(cache_key)
            
            # Check memory limits
            if (self.stats['size_bytes'] + size_bytes > self.stats['max_size_bytes']):
                self.logger.warning("Cache memory limit exceeded, evicting entries")
                self._evict_lru()
            
            # Create new entry
            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=current_time,
                expires_at=expires_at,
                size_bytes=size_bytes
            )
            
            # Add to cache
            self.cache[cache_key] = entry
            self.stats['size_bytes'] += size_bytes
            
            # Evict LRU if needed
            if len(self.cache) > self.max_size:
                self._evict_lru()
    
    def delete(self, key: Union[str, tuple]) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted
        """
        with self._lock:
            cache_key = self._generate_key(key)
            if cache_key in self.cache:
                self._remove_entry(cache_key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.stats['size_bytes'] = 0
            self.stats['evictions'] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = 0.0
            total_requests = self.stats['hits'] + self.stats['misses']
            if total_requests > 0:
                hit_rate = self.stats['hits'] / total_requests
            
            return {
                'entries': len(self.cache),
                'max_size': self.max_size,
                'size_bytes': self.stats['size_bytes'],
                'max_size_bytes': self.stats['max_size_bytes'],
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'memory_usage_percent': (self.stats['size_bytes'] / self.stats['max_size_bytes']) * 100
            }


class DatabaseConnectionPool:
    """
    SQLite database connection pool for improved performance
    """
    
    def __init__(self, database_path: str, pool_size: int = 10, timeout: float = 30.0):
        """
        Initialize connection pool
        
        Args:
            database_path: Path to SQLite database
            pool_size: Maximum number of connections
            timeout: Connection timeout in seconds
        """
        self.database_path = database_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.connections = []
        self.in_use = set()
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('database_pool')
        
        # Pre-create connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create initial connection pool"""
        for _ in range(self.pool_size):
            try:
                conn = sqlite3.connect(
                    self.database_path,
                    timeout=self.timeout,
                    check_same_thread=False
                )
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.row_factory = sqlite3.Row
                self.connections.append(conn)
            except Exception as e:
                self.logger.error(f"Failed to create database connection: {e}")
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get database connection from pool
        
        Returns:
            SQLite connection
        """
        with self._lock:
            # Find available connection
            for conn in self.connections:
                if conn not in self.in_use:
                    self.in_use.add(conn)
                    return conn
            
            # No available connections, create new one if under limit
            if len(self.connections) < self.pool_size:
                try:
                    conn = sqlite3.connect(
                        self.database_path,
                        timeout=self.timeout,
                        check_same_thread=False
                    )
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.row_factory = sqlite3.Row
                    self.connections.append(conn)
                    self.in_use.add(conn)
                    return conn
                except Exception as e:
                    self.logger.error(f"Failed to create new connection: {e}")
            
            # All connections in use, wait and retry
            raise Exception("No database connections available")
    
    def return_connection(self, conn: sqlite3.Connection):
        """
        Return connection to pool
        
        Args:
            conn: Connection to return
        """
        with self._lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
    
    def close_all(self):
        """Close all connections in pool"""
        with self._lock:
            for conn in self.connections:
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()
            self.in_use.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                'total_connections': len(self.connections),
                'in_use': len(self.in_use),
                'available': len(self.connections) - len(self.in_use),
                'pool_size': self.pool_size
            }


class QueryOptimizer:
    """
    Database query optimization and caching
    """
    
    def __init__(self, cache: InMemoryCache, connection_pool: DatabaseConnectionPool):
        """
        Initialize query optimizer
        
        Args:
            cache: Cache instance
            connection_pool: Database connection pool
        """
        self.cache = cache
        self.connection_pool = connection_pool
        self.query_stats = defaultdict(lambda: {'count': 0, 'total_time': 0.0, 'avg_time': 0.0})
        self._lock = threading.RLock()
        self.logger = system_monitor.get_logger('query_optimizer')
    
    def execute_cached_query(self, query: str, params: tuple = None, 
                           cache_ttl: int = 300) -> List[Dict]:
        """
        Execute query with caching
        
        Args:
            query: SQL query
            params: Query parameters
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Query results
        """
        # Generate cache key
        cache_key = (query, params or ())
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Execute query
        start_time = time.time()
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results and convert to list of dicts
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            # Update query statistics
            execution_time = time.time() - start_time
            with self._lock:
                stats = self.query_stats[query]
                stats['count'] += 1
                stats['total_time'] += execution_time
                stats['avg_time'] = stats['total_time'] / stats['count']
            
            # Cache results
            self.cache.set(cache_key, results, ttl=cache_ttl)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", query=query, params=params)
            raise
        finally:
            if conn:
                self.connection_pool.return_connection(conn)
    
    def get_query_stats(self) -> Dict[str, Dict]:
        """Get query performance statistics"""
        with self._lock:
            return dict(self.query_stats)


class ResponseCompressor:
    """
    HTTP response compression for better performance
    """
    
    @staticmethod
    def compress_response(data: str, compression_level: int = 6) -> bytes:
        """
        Compress response data using gzip
        
        Args:
            data: Response data as string
            compression_level: Compression level (1-9)
            
        Returns:
            Compressed data as bytes
        """
        return gzip.compress(data.encode('utf-8'), compresslevel=compression_level)
    
    @staticmethod
    def should_compress(data: str, min_size: int = 1000) -> bool:
        """
        Determine if response should be compressed
        
        Args:
            data: Response data
            min_size: Minimum size in bytes to compress
            
        Returns:
            True if should compress
        """
        return len(data.encode('utf-8')) >= min_size


class PerformanceOptimizer:
    """
    Main performance optimization coordinator
    """
    
    def __init__(self, database_path: str = "trading_platform.db"):
        """
        Initialize performance optimizer
        
        Args:
            database_path: Path to database
        """
        self.cache = InMemoryCache(max_size=5000, default_ttl=1800)  # 30 min default
        self.connection_pool = DatabaseConnectionPool(database_path, pool_size=15)
        self.query_optimizer = QueryOptimizer(self.cache, self.connection_pool)
        self.compressor = ResponseCompressor()
        self.logger = system_monitor.get_logger('performance_optimizer')
        
        # Performance monitoring
        self.request_times = deque(maxlen=1000)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0, 'total_time': 0.0, 'avg_time': 0.0, 'errors': 0
        })
        self._lock = threading.RLock()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        return {
            'cache': self.cache.get_stats(),
            'database_pool': self.connection_pool.get_stats(),
            'query_stats': self.query_optimizer.get_query_stats(),
            'endpoint_stats': dict(self.endpoint_stats),
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_all_caches(self) -> Dict[str, Any]:
        """Clear all caches and return statistics"""
        old_stats = self.cache.get_stats()
        self.cache.clear()
        
        return {
            'cleared_entries': old_stats['entries'],
            'freed_bytes': old_stats['size_bytes'],
            'timestamp': datetime.now().isoformat()
        }


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


# Performance decorators
def cached_endpoint(ttl: int = 300):
    """
    Decorator for caching endpoint responses
    
    Args:
        ttl: Cache TTL in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached_result = performance_optimizer.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            performance_optimizer.cache.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


def monitor_performance(endpoint_name: str = None):
    """
    Decorator to monitor endpoint performance
    
    Args:
        endpoint_name: Custom endpoint name for stats
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = endpoint_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful execution
                execution_time = time.time() - start_time
                with performance_optimizer._lock:
                    stats = performance_optimizer.endpoint_stats[name]
                    stats['count'] += 1
                    stats['total_time'] += execution_time
                    stats['avg_time'] = stats['total_time'] / stats['count']
                
                return result
                
            except Exception as e:
                # Record error
                execution_time = time.time() - start_time
                with performance_optimizer._lock:
                    stats = performance_optimizer.endpoint_stats[name]
                    stats['errors'] += 1
                    stats['count'] += 1
                    stats['total_time'] += execution_time
                    stats['avg_time'] = stats['total_time'] / stats['count']
                
                raise
        return wrapper
    return decorator


def database_transaction(read_only: bool = False):
    """
    Decorator for database transactions with connection pooling
    
    Args:
        read_only: Whether this is a read-only transaction
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = performance_optimizer.connection_pool.get_connection()
                
                if not read_only:
                    conn.execute("BEGIN IMMEDIATE")
                
                # Inject connection as first argument
                result = func(conn, *args, **kwargs)
                
                if not read_only:
                    conn.commit()
                
                return result
                
            except Exception as e:
                if conn and not read_only:
                    conn.rollback()
                performance_optimizer.logger.error(f"Database transaction failed: {e}")
                raise
            finally:
                if conn:
                    performance_optimizer.connection_pool.return_connection(conn)
        return wrapper
    return decorator