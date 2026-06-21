from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import ValidityModels

class ValidityAnalysisController:
    """Controller for Validity Analysis page operations with caching"""
    
    @staticmethod
    def get_validity_stats() -> Dict:
        """Get validity statistics (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('validity_stats', cache_params)
        if cached:
            return cached
        
        # Use fast pre-computed method (OPTIMIZED)
        result = ValidityModels.get_validity_stats_fast()
        cache.set('validity_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_validity_distribution() -> List[Dict]:
        """Get validity period distribution (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('validity_distribution', cache_params)
        if cached:
            return cached
        
        # Use fast pre-computed method (OPTIMIZED)
        result = ValidityModels.get_validity_distribution_fast()
        cache.set('validity_distribution', cache_params, result)
        return result
    
    @staticmethod
    def get_issuance_timeline(months: int = 12) -> List:
        """Get certificate issuance timeline (cached 15 min) - USES FAST PRE-COMPUTED METHOD"""
        cache_params = {'months': months}
        
        cached = cache.get('issuance_timeline', cache_params)
        if cached:
            return cached
        
        result = ValidityModels.get_issuance_timeline_fast(months)
        cache.set('issuance_timeline', cache_params, result)
        return result