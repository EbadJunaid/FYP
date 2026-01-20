# backend/certificates/controllers.py
# Business logic layer for certificate operations with Redis caching

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from .models import CertificateModel
from .cache_service import cache


@dataclass
class GlobalFilterParams:
    """Dataclass to hold global filter parameters"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    countries: Optional[List[str]] = None
    issuers: Optional[List[str]] = None
    grades: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    validation_levels: Optional[List[str]] = None
    
    def to_cache_key(self) -> Dict:
        """Convert to dict for cache key generation"""
        return {
            k: v for k, v in asdict(self).items() 
            if v is not None and (not isinstance(v, list) or len(v) > 0)
        }
    
    def has_filters(self) -> bool:
        """Check if any filters are active"""
        return any([
            self.start_date, self.end_date,
            self.countries and len(self.countries) > 0,
            self.issuers and len(self.issuers) > 0,
            self.grades and len(self.grades) > 0,
            self.statuses and len(self.statuses) > 0,
            self.validation_levels and len(self.validation_levels) > 0
        ])


class DashboardController:
    """Controller for dashboard-related operations"""
    
    @staticmethod
    def get_global_health() -> Dict:
        """Get global health metrics for dashboard (cached 5 min)"""
        cache_params = {}
        
        # Try cache first
        cached = cache.get('metrics', cache_params)
        if cached:
            return cached
        
        # Query MongoDB
        result = CertificateModel.get_dashboard_metrics()
        
        # Cache result
        cache.set('metrics', cache_params, result)
        return result
    
    @staticmethod
    def get_recent_scans(page: int = 1, page_size: int = 10) -> Dict:
        """Get recent certificate scans for table (cached 3 min)"""
        cache_params = {'page': page, 'page_size': page_size}
        
        cached = cache.get('certificates', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_all(page=page, page_size=page_size)
        cache.set('certificates', cache_params, result)
        return result


class CertificateController:
    """Controller for certificate CRUD operations"""
    
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
            base_filter = CertificateModel.build_filter_query(
                start_date=global_filters.start_date,
                end_date=global_filters.end_date,
                countries=global_filters.countries,
                issuers=global_filters.issuers,
                grades=global_filters.grades,
                statuses=global_filters.statuses,
                validation_levels=global_filters.validation_levels
            )
        
        # Query MongoDB with both specific and global filters
        result = CertificateModel.get_all(
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
    
    @staticmethod
    def get_certificate_by_id(cert_id: str) -> Optional[Dict]:
        """Get single certificate by ID (not cached - individual lookups)"""
        return CertificateModel.get_by_id(cert_id)
    
    @staticmethod
    def search_certificates(query: str, page: int = 1, page_size: int = 10) -> Dict:
        """Search certificates by domain (cached 3 min)"""
        cache_params = {'search': query, 'page': page, 'page_size': page_size}
        
        cached = cache.get('certificates', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_all(page=page, page_size=page_size, search=query)
        cache.set('certificates', cache_params, result)
        return result


class AnalyticsController:
    """Controller for analytics and chart data"""
    
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
            base_filter = CertificateModel.build_filter_query(
                start_date=global_filters.start_date,
                end_date=global_filters.end_date,
                countries=global_filters.countries,
                issuers=global_filters.issuers,
                grades=global_filters.grades,
                statuses=global_filters.statuses,
                validation_levels=global_filters.validation_levels
            )
        
        result = CertificateModel.get_encryption_strength(base_filter=base_filter)
        cache.set('encryption', cache_params, result)
        return result
    
    @staticmethod
    def get_validity_trends(months_before: int = 4, months_after: int = 4, granularity: str = 'monthly') -> List[Dict]:
        """Get validity trends for line chart (cached 15 min)"""
        cache_params = {'months_before': months_before, 'months_after': months_after, 'granularity': granularity}
        
        cached = cache.get('validity_trends', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validity_trends(
            months_before=months_before, 
            months_after=months_after,
            granularity=granularity
        )
        cache.set('validity_trends', cache_params, result)
        return result
    
    @staticmethod
    def get_ca_leaderboard(limit: int = 10, global_filters: Optional[GlobalFilterParams] = None) -> List[Dict]:
        """Get CA leaderboard for chart (cached 5 min)"""
        cache_params = {'limit': limit, **(global_filters.to_cache_key() if global_filters else {})}
        
        cached = cache.get('ca_analytics', cache_params)
        if cached:
            return cached
        
        # Build base filter from global params
        base_filter = None
        if global_filters and global_filters.has_filters():
            base_filter = CertificateModel.build_filter_query(
                start_date=global_filters.start_date,
                end_date=global_filters.end_date,
                countries=global_filters.countries,
                issuers=global_filters.issuers,
                grades=global_filters.grades,
                statuses=global_filters.statuses,
                validation_levels=global_filters.validation_levels
            )
        
        result = CertificateModel.get_ca_distribution(limit=limit, base_filter=base_filter)
        cache.set('ca_analytics', cache_params, result)
        return result
    
    @staticmethod
    def get_ca_stats() -> Dict:
        """Get CA stats for metric cards (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('ca_stats', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_ca_stats()
        cache.set('ca_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_validation_distribution() -> List[Dict]:
        """Get validation level distribution (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('validation_dist', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validation_distribution()
        cache.set('validation_dist', cache_params, result)
        return result
    
    @staticmethod
    def get_issuer_validation_matrix(limit: int = 10) -> List[Dict]:
        """Get issuer x validation level matrix (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('issuer_validation_matrix', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_issuer_validation_matrix(limit=limit)
        cache.set('issuer_validation_matrix', cache_params, result)
        return result
    
    @staticmethod
    def get_geographic_distribution(limit: int = 10, global_filters: Optional[GlobalFilterParams] = None) -> List[Dict]:
        """Get geographic distribution for chart (cached 5 min)"""
        cache_params = {'limit': limit, **(global_filters.to_cache_key() if global_filters else {})}
        
        cached = cache.get('geographic', cache_params)
        if cached:
            return cached
        
        # Build base filter from global params
        base_filter = None
        if global_filters and global_filters.has_filters():
            base_filter = CertificateModel.build_filter_query(
                start_date=global_filters.start_date,
                end_date=global_filters.end_date,
                countries=global_filters.countries,
                issuers=global_filters.issuers,
                grades=global_filters.grades,
                statuses=global_filters.statuses,
                validation_levels=global_filters.validation_levels
            )
        
        result = CertificateModel.get_geographic_distribution(limit=limit, base_filter=base_filter)
        cache.set('geographic', cache_params, result)
        return result
    
    @staticmethod
    def get_filter_options() -> Dict:
        """Get unique filter options (cached 30 min)"""
        cache_params = {}
        
        cached = cache.get('unique_filters', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_unique_filters()
        cache.set('unique_filters', cache_params, result)
        return result
    
    @staticmethod
    def get_future_risk() -> Dict:
        """Get future risk prediction data (cached 15 min)"""
        cache_params = {}
        
        cached = cache.get('future_risk', cache_params)
        if cached:
            return cached
        
        # Calculate risk from metrics
        metrics = CertificateModel.get_dashboard_metrics()
        expiring = metrics['expiringSoon']['count']
        critical = metrics['criticalVulnerabilities']['count']
        
        # Calculate risk level
        if critical > 5 or expiring > 20:
            risk_level = 'High'
            confidence = 92
        elif critical > 2 or expiring > 10:
            risk_level = 'Medium'
            confidence = 78
        else:
            risk_level = 'Low'
            confidence = 65
        
        result = {
            'confidenceLevel': confidence,
            'riskLevel': risk_level,
            'projectedThreats': [
                {
                    'id': '1',
                    'title': 'Weak Key Rotation',
                    'description': f'Predicted in 3 months',
                    'timeframe': '3 months',
                    'icon': 'key'
                },
                {
                    'id': '2',
                    'title': 'Signature Expiry',
                    'description': f'Watch for SHA-1 risk',
                    'timeframe': '6 months',
                    'icon': 'signature'
                }
            ]
        }
        
        cache.set('future_risk', cache_params, result)
        return result


class ValidityAnalysisController:
    """Controller for validity analysis page data"""
    
    @staticmethod
    def get_validity_stats() -> Dict:
        """Get validity statistics (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('validity_stats', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validity_stats()
        cache.set('validity_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_validity_distribution() -> List[Dict]:
        """Get validity period distribution (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('validity_distribution', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validity_distribution()
        cache.set('validity_distribution', cache_params, result)
        return result
    
    # @staticmethod
    # def get_issuance_timeline() -> List[Dict]:
    #     """Get issuance and expiration timeline (cached 5 min)"""
    #     cache_params = {}
        
    #     cached = cache.get('issuance_timeline', cache_params)
    #     if cached:
    #         return cached
        
    #     result = CertificateModel.get_issuance_timeline()
    #     cache.set('issuance_timeline', cache_params, result)
    #     return result


class NotificationController:
    """Controller for notification-related operations"""
    
    @staticmethod
    def get_notifications() -> Dict:
        """Get all notifications (cached 2 min - time sensitive)"""
        cache_params = {}
        
        cached = cache.get('notifications', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_notifications()
        cache.set('notifications', cache_params, result)
        return result


class SANAnalyticsController:
    """Controller for SAN (Subject Alternative Name) Analytics operations"""
    
    @staticmethod
    def get_san_stats() -> Dict:
        """Get SAN statistics for metric cards (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_stats', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_san_stats()
        cache.set('san_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_san_distribution() -> List[Dict]:
        """Get SAN count distribution histogram (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_distribution', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_san_distribution()
        cache.set('san_distribution', cache_params, result)
        return result
    
    @staticmethod
    def get_san_tld_breakdown(limit: int = 10) -> List[Dict]:
        """Get top TLDs from SAN entries (cached 15 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('san_tld', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_san_tld_breakdown(limit=limit)
        cache.set('san_tld', cache_params, result)
        return result
    
    @staticmethod
    def get_san_wildcard_breakdown() -> Dict:
        """Get wildcard vs standard SAN breakdown (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('san_wildcard', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_san_wildcard_breakdown()
        cache.set('san_wildcard', cache_params, result)
        return result


class TrendsController:
    """Controller for trends analytics with caching"""
    
    @staticmethod
    def get_trends_stats() -> Dict:
        """Get trends metric card stats (cached 10 min)"""
        cache_params = {}
        
        cached = cache.get('trends_stats', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_trends_stats()
        cache.set('trends_stats', cache_params, result)
        return result
    
    @staticmethod
    def get_issuance_timeline(months: int = 12) -> List:
        """Get certificate issuance timeline (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('issuance_timeline', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_issuance_timeline(months)
        cache.set('issuance_timeline', cache_params, result)
        return result
    
    @staticmethod
    def get_expiration_forecast(months: int = 12) -> List:
        """Get certificate expiration forecast (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('expiration_forecast', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_expiration_forecast(months)
        cache.set('expiration_forecast', cache_params, result)
        return result
    
    @staticmethod
    def get_algorithm_adoption(months: int = 12) -> List:
        """Get algorithm adoption trends (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('algorithm_adoption', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_algorithm_adoption(months)
        cache.set('algorithm_adoption', cache_params, result)
        return result
    
    @staticmethod
    def get_validation_level_trends(months: int = 12) -> List:
        """Get validation level trends (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('validation_trends', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validation_level_trends(months)
        cache.set('validation_trends', cache_params, result)
        return result
    
    @staticmethod
    def get_key_size_timeline(months: int = 12) -> List:
        """Get key size distribution timeline for animation (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('key_size_timeline', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_key_size_timeline(months)
        cache.set('key_size_timeline', cache_params, result)
        return result


class SharedKeyController:
    """Controller for shared public key analytics"""
    
    @staticmethod
    def get_stats() -> Dict:
        """Get shared key stats (cached 10 min)"""
        cached = cache.get('shared_key_stats', {})
        if cached:
            return cached
        
        result = CertificateModel.get_shared_key_stats()
        cache.set('shared_key_stats', {}, result, ttl=600)
        return result
    
    @staticmethod
    def get_distribution() -> List:
        """Get shared key group size distribution (cached 10 min)"""
        cached = cache.get('shared_key_distribution', {})
        if cached:
            return cached
        
        result = CertificateModel.get_shared_key_distribution()
        cache.set('shared_key_distribution', {}, result, ttl=600)
        return result
    
    @staticmethod
    def get_by_issuer(limit: int = 10) -> List:
        """Get shared key certs by issuer (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('shared_key_issuer', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_shared_keys_by_issuer(limit)
        cache.set('shared_key_issuer', cache_params, result, ttl=600)
        return result
    
    @staticmethod
    def get_timeline(months: int = 12) -> List:
        """Get shared key timeline (cached 15 min)"""
        cache_params = {'months': months}
        
        cached = cache.get('shared_key_timeline', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_shared_key_timeline(months)
        cache.set('shared_key_timeline', cache_params, result, ttl=900)
        return result
    
    @staticmethod
    def get_heatmap(limit: int = 10) -> List:
        """Get issuer x key-type heatmap (cached 10 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('shared_key_heatmap', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_shared_key_heatmap(limit)
        cache.set('shared_key_heatmap', cache_params, result, ttl=600)
        return result


class CacheController:
    """Controller for cache management operations"""
    
    @staticmethod
    def get_cache_stats() -> Dict:
        """Get cache statistics"""
        return cache.get_stats()
    
    @staticmethod
    def clear_all_caches() -> Dict:
        """Clear all caches (admin operation)"""
        cache.clear_all()
        return {'status': 'success', 'message': 'All caches cleared'}
    
    @staticmethod
    def invalidate_certificates() -> Dict:
        """Invalidate certificate caches (e.g., after new scan)"""
        cache.invalidate_namespace('certificates')
        cache.invalidate_namespace('metrics')
        cache.invalidate_namespace('notifications')
        return {'status': 'success', 'message': 'Certificate caches invalidated'}

