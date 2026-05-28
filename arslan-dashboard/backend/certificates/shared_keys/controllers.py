from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import SharedKeyModel


class SharedKeyController:
    """Controller for shared public key analytics"""
    
    @staticmethod
    def get_stats() -> Dict:
        """⚡ OPTIMIZED: Get shared key stats from materialized view (cached 10 min)"""
        cached = cache.get('shared_key_stats', {})
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_key_stats_fast()  # ⚡ Changed to fast version
        cache.set('shared_key_stats', {}, result, ttl=600)
        return result
    
    @staticmethod
    def get_distribution() -> List:
        """⚡ OPTIMIZED: Get shared key distribution from materialized view (cached 10 min)"""
        cached = cache.get('shared_key_distribution', {})
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_key_distribution_fast()  # ⚡ Changed to fast version
        cache.set('shared_key_distribution', {}, result, ttl=600)
        return result
    
    @staticmethod
    def get_by_issuer(limit: int = 10) -> List:
        """⚡ OPTIMIZED: Get shared key certs by issuer from materialized view (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('shared_key_issuer', cache_params)
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_keys_by_issuer_fast(limit)  # ⚡ Changed to fast version
        cache.set('shared_key_issuer', cache_params, result, ttl=600)
        return result
    
    @staticmethod
    def get_timeline(months: int = 12) -> List:
        """⚡ OPTIMIZED: Get shared key timeline from materialized view (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('shared_key_timeline', cache_params)
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_key_timeline_fast(months)  # ⚡ Changed to fast version
        cache.set('shared_key_timeline', cache_params, result, ttl=900)
        return result
    
    @staticmethod
    def get_heatmap(limit: int = 10) -> List:
        """⚡ OPTIMIZED: Get issuer x key-type heatmap from materialized view (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('shared_key_heatmap', cache_params)
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_key_heatmap_fast(limit)  # ⚡ Changed to fast version
        cache.set('shared_key_heatmap', cache_params, result, ttl=600)
        return result
    
    @staticmethod
    def get_list(page: int = 1, page_size: int = 10, sort_by: str = 'certificate_count', 
                 sort_order: str = 'desc', risk_level: str = None, key_type: str = None,
                 min_cert_count: int = None, issuer: str = None) -> Dict:
        """Get paginated list of shared key groups for table view (cached 5 min)"""
        cache_params = {
            'page': page, 
            'page_size': page_size,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'risk_level': risk_level,
            'key_type': key_type,
            'min_cert_count': min_cert_count,
            'issuer': issuer
        }
        
        cached = cache.get('shared_keys_list', cache_params)
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_keys_list(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            risk_level=risk_level,
            key_type=key_type,
            min_cert_count=min_cert_count,
            issuer=issuer
        )
        
        cache.set('shared_keys_list', cache_params, result, ttl=300)  # Cache for 5 minutes
        return result
    
    @staticmethod
    def get_detail(public_key_hash: str) -> Dict:
        """Get full details for a specific shared key group (cached 10 min)"""
        cache_params = {'public_key_hash': public_key_hash}
        
        cached = cache.get('shared_key_detail', cache_params)
        if cached:
            return cached
        
        result = SharedKeyModel.get_shared_key_detail(public_key_hash)
        cache.set('shared_key_detail', cache_params, result, ttl=600)
        return result
