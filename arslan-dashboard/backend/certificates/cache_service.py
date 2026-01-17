"""
Redis Cache Service for SSL Guardian
Provides server-side caching to reduce MongoDB query load.

Features:
- Key-value caching with TTL (Time-To-Live)
- Consistent cache key generation
- Namespace-based invalidation
- Graceful fallback when Redis is unavailable OR not installed
"""

# Try to import redis - graceful fallback if not installed
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

import json
import hashlib
import logging
from typing import Any, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Log if Redis library is not available
if not REDIS_AVAILABLE:
    logger.warning("[CACHE] Redis library not installed. Run 'pip install redis' to enable caching.")
    logger.warning("[CACHE] Application will continue without caching (all queries hit MongoDB).")


# TTL configurations in seconds (reduced for fresher data)
TTL_CONFIG = {
    'metrics': 300,              # 5 minutes
    'certificates': 300,         # 5 minutes (for pages 2+)
    'certificates_page1': 900,   # 15 minutes (first page)
    'ca_analytics': 480,         # 8 minutes
    'ca_stats': 300,             # 5 minutes (CA metric cards)
    'validation_dist': 300,      # 5 minutes (validation level distribution)
    'issuer_validation_matrix': 600,  # 10 minutes (CA validation heatmap)
    'encryption': 480,           # 8 minutes
    'validity_trends': 480,      # 8 minutes
    'geographic': 480,           # 8 minutes
    'future_risk': 480,          # 8 minutes
    'notifications': 120,         # 2 minute (time-sensitive)
    'unique_filters': 480,       # 8 minutes
    # Signature and Hashes page caches
    'signature_stats': 480,      # 8 minutes
    'hash_trends': 600,          # 10 minutes (historical data)
    'issuer_matrix': 600,        # 10 minutes
    # SAN Analytics page caches
    'san_stats': 600,            # 10 minutes
    'san_distribution': 600,     # 10 minutes
    'san_tld': 900,              # 15 minutes
    'san_wildcard': 600,         # 10 minutes
}


class CacheService:
    """
    Redis-based caching service for SSL Guardian.
    
    Provides:
    - get/set operations with automatic serialization
    - TTL-based expiration
    - Namespace-based cache invalidation
    - Graceful fallback when Redis unavailable or not installed
    
    IMPORTANT: If redis library is not installed, all methods are no-ops
    and return None/empty values. The app will work but without caching.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to reuse connection"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.prefix = 'ssl_guardian'
        self.redis_client = None
        self.redis_installed = REDIS_AVAILABLE
        
        if self.redis_installed:
            self._connect()
        else:
            logger.info("[CACHE] Skipping Redis connection (library not installed)")
        
        self._initialized = True
    
    def _connect(self):
        """Initialize Redis connection with error handling"""
        if not self.redis_installed:
            return
        
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("[CACHE] Connected to Redis successfully")
        except redis.ConnectionError as e:
            logger.warning(f"[CACHE] Redis server not running, caching disabled: {e}")
            logger.info("[CACHE] Start Redis server or run 'docker run -d -p 6379:6379 redis:alpine'")
            self.redis_client = None
        except Exception as e:
            logger.error(f"[CACHE] Unexpected error connecting to Redis: {e}")
            self.redis_client = None
    
    def _make_key(self, namespace: str, params: Dict) -> str:
        """
        Generate consistent cache key from namespace and params.
        
        Format: ssl_guardian:{namespace}:{hash}
        Hash ensures unique key for different parameter combinations.
        """
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        hash_val = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        return f"{self.prefix}:{namespace}:{hash_val}"
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.redis_installed or not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def get(self, namespace: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            namespace: Cache category (e.g., 'certificates', 'metrics')
            params: Query parameters to identify specific cache entry
            
        Returns:
            Cached data or None if not found/unavailable
        """
        if not self.redis_installed or not self.redis_client:
            return None
        
        params = params or {}
        key = self._make_key(namespace, params)
        
        try:
            data = self.redis_client.get(key)
            if data:
                logger.info(f"[CACHE HIT] {namespace}:{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}")
                return json.loads(data)
            logger.info(f"[CACHE MISS] {namespace}:{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}")
            return None
        except Exception as e:
            logger.error(f"[CACHE] Get error for {namespace}: {e}")
            return None
    
    def set(self, namespace: str, params: Optional[Dict], value: Any, ttl: Optional[int] = None):
        """
        Cache value with TTL.
        
        Args:
            namespace: Cache category
            params: Query parameters to identify specific cache entry
            value: Data to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses TTL_CONFIG default if not specified)
        """
        if not self.redis_installed or not self.redis_client:
            return
        
        params = params or {}
        key = self._make_key(namespace, params)
        
        # Use configured TTL if not specified
        if ttl is None:
            ttl = TTL_CONFIG.get(namespace, 300)
        
        try:
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"[CACHE SET] {namespace} with TTL={ttl}s")
        except Exception as e:
            logger.error(f"[CACHE] Set error for {namespace}: {e}")
    
    def delete(self, namespace: str, params: Optional[Dict] = None):
        """Delete specific cache entry"""
        if not self.redis_installed or not self.redis_client:
            return
        
        params = params or {}
        key = self._make_key(namespace, params)
        
        try:
            self.redis_client.delete(key)
            logger.debug(f"[CACHE DELETE] {key}")
        except Exception as e:
            logger.error(f"[CACHE] Delete error: {e}")
    
    def invalidate_namespace(self, namespace: str):
        """
        Invalidate all cache entries in a namespace.
        
        Useful when data changes (e.g., after new scan).
        """
        if not self.redis_installed or not self.redis_client:
            return
        
        pattern = f"{self.prefix}:{namespace}:*"
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"[CACHE INVALIDATE] Cleared {len(keys)} keys in {namespace}")
        except Exception as e:
            logger.error(f"[CACHE] Invalidate error for {namespace}: {e}")
    
    def clear_all(self):
        """Clear all SSL Guardian caches"""
        if not self.redis_installed or not self.redis_client:
            return
        
        pattern = f"{self.prefix}:*"
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"[CACHE CLEAR] Cleared all {len(keys)} cached keys")
        except Exception as e:
            logger.error(f"[CACHE] Clear all error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        if not self.redis_installed:
            return {
                'status': 'unavailable',
                'reason': 'Redis library not installed. Run: pip install redis'
            }
        
        if not self.redis_client:
            return {
                'status': 'unavailable',
                'reason': 'Redis server not running. Start with: docker run -d -p 6379:6379 redis:alpine'
            }
        
        try:
            pattern = f"{self.prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            by_namespace = {}
            for key in keys:
                parts = key.split(':')
                if len(parts) >= 2:
                    ns = parts[1]
                    by_namespace[ns] = by_namespace.get(ns, 0) + 1
            
            return {
                'status': 'connected',
                'total_keys': len(keys),
                'by_namespace': by_namespace,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# Singleton instance
cache = CacheService()
