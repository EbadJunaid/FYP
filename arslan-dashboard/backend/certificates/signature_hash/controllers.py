from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import SignatureHashModel

class SignatureHashController:
    """Controller for Signature & Hash Analytics operations with caching"""
    
    @staticmethod
    def get_signature_stats():
        """⚡ OPTIMIZED: Get signature stats from materialized view (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('signature_stats', cache_params)
        if cached:
            return cached
        
        result = SignatureHashModel.get_signature_stats_fast()
        cache.set('signature_stats', cache_params, result, ttl=300)
        return result
    
    @staticmethod
    def get_hash_trends(months=36, granularity='quarterly'):
        """⚡ OPTIMIZED: Get hash trends from materialized view (cached 10 min)"""
        # Validate granularity
        if granularity not in ['quarterly', 'yearly']:
            granularity = 'quarterly'
        
        cache_params = {'months': months, 'granularity': granularity}
        
        cached = cache.get('hash_trends', cache_params)
        if cached:
            return cached
        
        result = SignatureHashModel.get_hash_trends_fast(months=months, granularity=granularity)
        cache.set('hash_trends', cache_params, result, ttl=600)
        return result
    
    @staticmethod
    def get_issuer_algorithm_matrix(limit=10):
        """⚡ OPTIMIZED: Get issuer algorithm matrix from materialized view (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('issuer_matrix', cache_params)
        if cached:
            return cached
        
        result = SignatureHashModel.get_issuer_algorithm_matrix_fast(limit=limit)
        cache.set('issuer_matrix', cache_params, result, ttl=600)
        return result
