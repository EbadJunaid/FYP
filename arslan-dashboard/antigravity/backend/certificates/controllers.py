# backend/certificates/controllers.py
# Business logic layer for certificate operations with Redis caching

from typing import Dict, List, Optional, Any
from .models import CertificateModel
from .cache_service import cache


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
        expiring_year: Optional[int] = None
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
            'expiring_year': expiring_year
        }
        
        # Use longer TTL (15 min) for page 1, shorter TTL (3 min) for other pages
        cache_namespace = 'certificates_page1' if page == 1 else 'certificates'
        
        # Try cache first
        cached = cache.get(cache_namespace, cache_params)
        if cached:
            return cached
        
        # Query MongoDB
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
            expiring_year=expiring_year
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
    def get_encryption_distribution() -> List[Dict]:
        """Get encryption strength distribution for chart (cached 15 min)"""
        cache_params = {}
        
        cached = cache.get('encryption', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_encryption_strength()
        cache.set('encryption', cache_params, result)
        return result
    
    @staticmethod
    def get_validity_trends(months_before: int = 4, months_after: int = 4) -> List[Dict]:
        """Get validity trends for line chart (cached 15 min)"""
        cache_params = {'months_before': months_before, 'months_after': months_after}
        
        cached = cache.get('validity_trends', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_validity_trends(months_before=months_before, months_after=months_after)
        cache.set('validity_trends', cache_params, result)
        return result
    
    @staticmethod
    def get_ca_leaderboard(limit: int = 10) -> List[Dict]:
        """Get CA leaderboard for chart (cached 15 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('ca_analytics', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_ca_distribution(limit=limit)
        cache.set('ca_analytics', cache_params, result)
        return result
    
    @staticmethod
    def get_geographic_distribution(limit: int = 10) -> List[Dict]:
        """Get geographic distribution for chart (cached 30 min)"""
        cache_params = {'limit': limit}
        
        cached = cache.get('geographic', cache_params)
        if cached:
            return cached
        
        result = CertificateModel.get_geographic_distribution(limit=limit)
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
