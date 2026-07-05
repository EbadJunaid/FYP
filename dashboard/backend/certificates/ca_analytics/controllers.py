from typing import List, Dict, Optional
from ..cache_service import cache
from .db_queries import CAModel


class CAAnalyticsController:
    """Controller for CA-page specific operations (uses local db_queries)."""

    @staticmethod
    def get_ca_stats() -> Dict:
        cache_params = {}
        cached = cache.get('ca_stats', cache_params)
        if cached:
            return cached
        result = CAModel.get_ca_stats_fast()
        # result = CAModel.get_ca_stats()

        cache.set('ca_stats', cache_params, result)
        return result

    @staticmethod
    def get_issuer_validation_matrix(limit: int = 10) -> List[Dict]:
        cache_params = {'limit': limit}
        cached = cache.get('issuer_validation_matrix', cache_params)
        if cached:
            return cached
        result = CAModel.get_issuer_validation_matrix_fast(limit=limit)
        cache.set('issuer_validation_matrix', cache_params, result)
        return result

    @staticmethod
    def get_ca_ranking(limit: int = 20, group_by: str = 'ca') -> Dict:
        return CAModel.get_ranking(limit=limit, group_by=group_by)
