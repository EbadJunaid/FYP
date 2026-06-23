from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import TrendsModel



class TrendsController:
    """Controller for trends analytics with caching"""
    
    @staticmethod
    def get_trends_stats() -> Dict:
        """Get trends metric card stats (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('trends_stats', cache_params)
        if cached:
            return cached
        
        result = TrendsModel.get_trends_stats()
        cache.set('trends_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_key_size_timeline(months: int = 12) -> List:
        """Get key size distribution timeline for animation (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('key_size_timeline', cache_params)
        if cached:
            return cached
        
        result = TrendsModel.get_key_size_timeline(months)
        cache.set('key_size_timeline', cache_params, result)
        return result

    @staticmethod
    def get_expiration_forecast(months: int = 12) -> List:
        """Get certificate expiration forecast (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('expiration_forecast', cache_params)
        if cached:
            return cached
        
        result = TrendsModel.get_expiration_forecast(months)
        cache.set('expiration_forecast', cache_params, result)
        return result
    
    @staticmethod
    def get_algorithm_adoption(months: int = 12) -> List:
        """Get algorithm adoption trends (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('algorithm_adoption', cache_params)
        if cached:
            return cached
        
        result = TrendsModel.get_algorithm_adoption(months)
        cache.set('algorithm_adoption', cache_params, result)
        return result
    
    @staticmethod
    def get_validation_level_trends(months: int = 12) -> List:
        """Get validation level trends (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('validation_trends', cache_params)
        if cached:
            return cached
        
        result = TrendsModel.get_validation_level_trends(months)
        cache.set('validation_trends', cache_params, result)
        return result