from ..cache_service import cache
from typing import List, Dict, Optional
from .db_queries import SharedModels


class GlobalFilterParams(object):
    """Dataclass to hold global filter parameters"""
    def __init__(self, start_date=None, end_date=None, countries=None, issuers=None, 
                 grades=None, statuses=None, validation_levels=None):
        self.start_date = start_date
        self.end_date = end_date
        self.countries = countries
        self.issuers = issuers
        self.grades = grades
        self.statuses = statuses
        self.validation_levels = validation_levels
    
    def to_cache_key(self):
        """Convert to dict for cache key generation"""
        result = {}
        if self.start_date:
            result['start_date'] = self.start_date
        if self.end_date:
            result['end_date'] = self.end_date
        if self.countries and len(self.countries) > 0:
            result['countries'] = tuple(self.countries)
        if self.issuers and len(self.issuers) > 0:
            result['issuers'] = tuple(self.issuers)
        if self.grades and len(self.grades) > 0:
            result['grades'] = tuple(self.grades)
        if self.statuses and len(self.statuses) > 0:
            result['statuses'] = tuple(self.statuses)
        if self.validation_levels and len(self.validation_levels) > 0:
            result['validation_levels'] = tuple(self.validation_levels)
        return result
    
    def has_filters(self):
        """Check if any filters are active"""
        return any([
            self.start_date, self.end_date,
            self.countries and len(self.countries) > 0,
            self.issuers and len(self.issuers) > 0,
            self.grades and len(self.grades) > 0,
            self.statuses and len(self.statuses) > 0,
            self.validation_levels and len(self.validation_levels) > 0
        ])


class SharedApisController(object):
    """Controller for Shared APIs with caching"""
    
    @staticmethod
    def get_global_health() -> Dict:
        """Get global health metrics for dashboard (cached 5 min)"""
        cache_params = {}
        
        # Try cache first
        cached = cache.get('metrics', cache_params)
        if cached:
            return cached
        
        # Query MongoDB
        result = SharedModels.get_dashboard_metrics()
        
        # Cache result
        cache.set('metrics', cache_params, result)
        return result
    
    @staticmethod
    def get_validity_trends(months_before: int = 4, months_after: int = 4, granularity: str = 'monthly') -> List[Dict]:
        """Get validity trends for line chart (cached 15 min)"""
        cache_params = {'months_before': months_before, 'months_after': months_after, 'granularity': granularity}
        
        cached = cache.get('validity_trends', cache_params)
        if cached:
            return cached
        
        result = SharedModels.get_validity_trends(
            months_before=months_before, 
            months_after=months_after,
            granularity=granularity
        )
        cache.set('validity_trends', cache_params, result)
        return result
    
    @staticmethod
    def get_ca_leaderboard(limit: int = 10, global_filters: Optional[GlobalFilterParams] = None) -> List[Dict]:
        """
        Get CA leaderboard for chart
        
        ⚡ OPTIMIZED: Uses pre-computed materialized view for fast response (~0.01s)
        Falls back to slow aggregation only if global filters are applied
        """
        cache_params = {'limit': limit, **(global_filters.to_cache_key() if global_filters else {})}
        
        cached = cache.get('ca_analytics', cache_params)
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
        
        # ⚡ Use fast pre-computed method (automatically falls back if filter provided)
        result = SharedModels.get_ca_distribution_fast(limit=limit, base_filter=base_filter)
        
        cache.set('ca_analytics', cache_params, result)
        return result
        
    @staticmethod
    def get_geographic_distribution(limit: int = 10, global_filters: Optional[GlobalFilterParams] = None) -> List[Dict]:
        """
        Get geographic distribution for chart
        
        ⚡ OPTIMIZED: Uses pre-computed materialized view for fast response (~0.01s)
        Falls back to slow aggregation only if global filters are applied
        """
        cache_params = {'limit': limit, **(global_filters.to_cache_key() if global_filters else {})}
        
        cached = cache.get('geographic', cache_params)
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
        
        # ⚡ Use fast pre-computed method (automatically falls back if filter provided)
        result = SharedModels.get_geographic_distribution_fast(limit=limit, base_filter=base_filter)
        
        cache.set('geographic', cache_params, result)
        return result
    

    @staticmethod
    def get_certificates(
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        country: Optional[str] = None,
        issuer: Optional[str] = None,
        search: Optional[str] = None,
        encryption_type: Optional[str] = None,
        has_vulnerabilities: Optional[bool] = None,
        expiring_month: Optional[int] = None,
        expiring_year: Optional[int] = None,
        expiring_days: Optional[int] = None,
        validity_bucket: Optional[str] = None,
        issued_month: Optional[int] = None,
        issued_year: Optional[int] = None,
        issued_within_days: Optional[int] = None,
        # Signature/Hash page filters
        signature_algorithm: Optional[str] = None,
        weak_hash: Optional[bool] = None,
        self_signed: Optional[bool] = None,
        key_size: Optional[int] = None,
        hash_type: Optional[str] = None,
        # SAN Analytics page filters
        san_tld: Optional[str] = None,
        san_type: Optional[str] = None,
        san_count_min: Optional[int] = None,
        san_count_max: Optional[int] = None,
        expiring_start: Optional[str] = None,
        expiring_end: Optional[str] = None,
        # Shared Keys page filter
        shared_key: Optional[bool] = None,
        # Global filter params
        global_filters: Optional[GlobalFilterParams] = None
    ) -> Dict:
        """Get paginated and filtered certificates (cached 3 min)"""
        if search:
            search = search.strip().lower()
            if not search:
                search = None

        cache_params = {
            'page': page,
            'page_size': page_size,
            'status': status,
            'country': country,
            'issuer': issuer,
            'search': search,
            'encryption_type': encryption_type,
            'has_vulnerabilities': has_vulnerabilities,
            'expiring_month': expiring_month,
            'expiring_year': expiring_year,
            'expiring_days': expiring_days,
            'validity_bucket': validity_bucket,
            'issued_month': issued_month,
            'issued_year': issued_year,
            'issued_within_days': issued_within_days,
            'signature_algorithm': signature_algorithm,
            'weak_hash': weak_hash,
            'self_signed': self_signed,
            'key_size': key_size,
            'hash_type': hash_type,
            'san_tld': san_tld,
            'san_type': san_type,
            'san_count_min': san_count_min,
            'san_count_max': san_count_max,
            'expiring_start': expiring_start,
            'expiring_end': expiring_end,
            'shared_key': shared_key,
            # Include global filter params in cache key
            **((global_filters.to_cache_key() if global_filters else {}))
        }
        
        # Use longer TTL (5 min) for page 1, shorter TTL (2 min) for other pages
        cache_namespace = 'certificates_page1' if page == 1 else 'certificates'
        
        # Try cache first
        cached = cache.get(cache_namespace, cache_params)
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
        
        # Query MongoDB with both specific and global filters
        result = SharedModels.get_all(
            page=page,
            page_size=page_size,
            status=status,
            country=country,
            issuer=issuer,
            search=search,
            encryption_type=encryption_type,
            has_vulnerabilities=has_vulnerabilities,
            expiring_month=expiring_month,
            expiring_year=expiring_year,
            expiring_days=expiring_days,
            validity_bucket=validity_bucket,
            issued_month=issued_month,
            issued_year=issued_year,
            issued_within_days=issued_within_days,
            signature_algorithm=signature_algorithm,
            weak_hash=weak_hash,
            self_signed=self_signed,
            key_size=key_size,
            hash_type=hash_type,
            san_tld=san_tld,
            san_type=san_type,
            san_count_min=san_count_min,
            san_count_max=san_count_max,
            expiring_start=expiring_start,
            expiring_end=expiring_end,
            shared_key=shared_key,
            base_filter=base_filter
        )
        
        # Cache result with appropriate TTL based on page
        cache.set(cache_namespace, cache_params, result)
        return result
    
    

    def get_certificate_by_id(cert_id: str) -> Optional[Dict]:
            """Get single certificate by ID (not cached - individual lookups)"""
            return SharedModels.get_by_id(cert_id)
    