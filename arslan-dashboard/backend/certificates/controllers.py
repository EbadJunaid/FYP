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
    
    @staticmethod
    def get_issuance_timeline() -> List[Dict]:
        """Get issuance and expiration timeline (cached 5 min)"""
        cache_params = {}
        
        cached = cache.get('issuance_timeline', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_issuance_timeline()
        cache.set('issuance_timeline', cache_params, result)
        return result


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
