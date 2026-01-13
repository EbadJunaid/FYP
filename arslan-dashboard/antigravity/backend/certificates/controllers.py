# backend/certificates/controllers.py
# Business logic layer for certificate operations

from typing import Dict, List, Optional, Any
from .models import CertificateModel


class DashboardController:
    """Controller for dashboard-related operations"""
    
    @staticmethod
    def get_global_health() -> Dict:
        """Get global health metrics for dashboard"""
        return CertificateModel.get_dashboard_metrics()
    
    @staticmethod
    def get_recent_scans(page: int = 1, page_size: int = 10) -> Dict:
        """Get recent certificate scans for table"""
        return CertificateModel.get_all(page=page, page_size=page_size)


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
        """Get paginated and filtered certificates"""
        return CertificateModel.get_all(
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
    
    @staticmethod
    def get_certificate_by_id(cert_id: str) -> Optional[Dict]:
        """Get single certificate by ID"""
        return CertificateModel.get_by_id(cert_id)
    
    @staticmethod
    def search_certificates(query: str, page: int = 1, page_size: int = 10) -> Dict:
        """Search certificates by domain"""
        return CertificateModel.get_all(page=page, page_size=page_size, search=query)


class AnalyticsController:
    """Controller for analytics and chart data"""
    
    @staticmethod
    def get_encryption_distribution() -> List[Dict]:
        """Get encryption strength distribution for chart"""
        return CertificateModel.get_encryption_strength()
    
    @staticmethod
    def get_validity_trends(months_before: int = 4, months_after: int = 4) -> List[Dict]:
        """Get validity trends for line chart - shows months before and after current"""
        return CertificateModel.get_validity_trends(months_before=months_before, months_after=months_after)
    
    @staticmethod
    def get_ca_leaderboard(limit: int = 10) -> List[Dict]:
        """Get CA leaderboard for chart"""
        return CertificateModel.get_ca_distribution(limit=limit)
    
    @staticmethod
    def get_geographic_distribution(limit: int = 10) -> List[Dict]:
        """Get geographic distribution for chart"""
        return CertificateModel.get_geographic_distribution(limit=limit)
    
    @staticmethod
    def get_filter_options() -> Dict:
        """Get unique filter options"""
        return CertificateModel.get_unique_filters()
    
    @staticmethod
    def get_future_risk() -> Dict:
        """Get future risk prediction data (mock for now)"""
        # This could be enhanced with ML predictions later
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
        
        return {
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


class NotificationController:
    """Controller for notification-related operations"""
    
    @staticmethod
    def get_notifications() -> Dict:
        """Get all notifications from real-time certificate data"""
        return CertificateModel.get_notifications()
