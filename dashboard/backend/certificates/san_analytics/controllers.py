from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import SANModel

class SANAnalyticsController:
    """Controller for SAN (Subject Alternative Name) Analytics operations"""
    
    @staticmethod
    def get_san_stats() -> Dict:
        """⚡ OPTIMIZED: Get SAN statistics from materialized view (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_stats', cache_params)
        if cached:
            return cached
        
        result = SANModel.get_san_stats_fast()  # ⚡ Changed to fast version
        cache.set('san_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_san_distribution() -> List[Dict]:
        """⚡ OPTIMIZED: Get SAN count distribution from materialized view (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_distribution', cache_params)
        if cached:
            return cached
        
        result = SANModel.get_san_distribution_fast()  # ⚡ Changed to fast version
        cache.set('san_distribution', cache_params, result)
        return result
    
    @staticmethod
    def get_san_tld_breakdown(limit: int = 10) -> List[Dict]:
        """⚡ OPTIMIZED: Get top TLDs from materialized view (cached 15 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('san_tld', cache_params)
        if cached:
            return cached
        
        result = SANModel.get_san_tld_breakdown_fast(limit=limit)  # ⚡ Changed to fast version
        cache.set('san_tld', cache_params, result)
        return result
    
    @staticmethod
    def get_san_wildcard_breakdown() -> Dict:
        """⚡ OPTIMIZED: Get wildcard vs standard from materialized view (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_wildcard', cache_params)
        if cached:
            return cached
        
        result = SANModel.get_san_wildcard_breakdown_fast()  # ⚡ Changed to fast version
        cache.set('san_wildcard', cache_params, result)
        return result
    
    @staticmethod
    def get_san_filtered_certs(filter_type: str, filter_value: str = None, 
                              page: int = 1, page_size: int = 50) -> Dict:
        """⚡ OPTIMIZED: Get filtered certificates from pre-computed collections (cached 2 min)"""
        cache_params = {
            'filter_type': filter_type,
            'filter_value': filter_value,
            'page': page,
            'page_size': page_size
        }
        
        cached = cache.get('san_filtered_certs', cache_params)
        if cached:
            return cached
        
        result = SANModel.get_san_filtered_certs_fast(
            filter_type=filter_type,
            filter_value=filter_value,
            page=page,
            page_size=page_size
        )
        cache.set('san_filtered_certs', cache_params, result)
        return result