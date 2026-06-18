from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import OverviewModels
#import from shared models...
from ..shared_apis.controllers import GlobalFilterParams
from ..shared_apis.db_queries import SharedModels


class OverviewController:
    """Controller for Overview page operations (uses local db_queries)."""
    @staticmethod
    def get_encryption_distribution(global_filters: Optional[GlobalFilterParams] = None) -> List[Dict]:
        """Get encryption strength distribution for chart (cached 5 min)"""
        cache_params = global_filters.to_cache_key() if global_filters else {}
        
        cached = cache.get('encryption', cache_params)
        if cached:
            return cached
        
        # Build base filter from global params
        base_filter = None
        if global_filters and global_filters.has_filters():
            base_filter = SharedModels.build_filter_query(
                start_date=global_filters.start_date,
                end_date=global_filters.end_date,
                countries=global_filters.countries,
                issuers=global_filters.issuers,
                grades=global_filters.grades,
                statuses=global_filters.statuses,
                validation_levels=global_filters.validation_levels
            )
        
        result = OverviewModels.get_encryption_strength(base_filter=base_filter)
        cache.set('encryption', cache_params, result)
        return result
    
    @staticmethod
    def get_filter_options() -> Dict:
        """Get unique filter options (cached 30 min)"""
        cache_params = {}
        
        cached = cache.get('unique_filters', cache_params)
        if cached:
            return cached
        
        result = OverviewModels.get_unique_filters()
        cache.set('unique_filters', cache_params, result)
        return result
    

    @staticmethod
    def get_future_risk() -> Dict:
        """Get future risk prediction data (cached 15 min)"""
        cache_params = {}
        
        cached = cache.get('future_risk', cache_params)
        if cached:
            return cached
        
        # # Calculate risk from metrics
        # metrics = CertificateModel.get_dashboard_metrics()    
        result = OverviewModels.get_future_risk()        
        cache.set('future_risk', cache_params, result)
        return result

    @staticmethod
    def get_vulnerabilities(page: int = 1, page_size: int = 10) -> Dict:
        """Get certificate vulnerability details for the overview vulnerabilities page"""
        cache_params = {}
        
        cached = cache.get('vulnerabilities', cache_params)
        if cached:
            return cached
        results = OverviewModels.get_vulnearablities(page=page, page_size=page_size)
        cache.set('vulnerabilities', cache_params, results)
    
