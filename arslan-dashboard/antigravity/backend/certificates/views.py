# backend/certificates/views.py
# Django REST Framework API Views

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .controllers import (
    DashboardController,
    CertificateController,
    AnalyticsController
)


def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response


@method_decorator(csrf_exempt, name='dispatch')
class GlobalHealthView(View):
    """
    GET /api/dashboard/global-health
    Returns overall health metrics for the dashboard
    """
    def get(self, request):
        try:
            metrics = DashboardController.get_global_health()
            return json_response(metrics)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CertificateListView(View):
    """
    GET /api/certificates
    Returns paginated list of certificates with optional filters
    Query params: page, page_size, status, country, issuer, search, encryption_type, has_vulnerabilities, expiring_month, expiring_year
    """
    def get(self, request):
        try:
            # Get query parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            status = request.GET.get('status')
            country = request.GET.get('country')
            issuer = request.GET.get('issuer')
            search = request.GET.get('search')
            encryption_type = request.GET.get('encryption_type')
            has_vulnerabilities = request.GET.get('has_vulnerabilities', '').lower() == 'true'
            
            # Expiring month/year filter (for validity trends clicks)
            expiring_month_str = request.GET.get('expiring_month')
            expiring_year_str = request.GET.get('expiring_year')
            expiring_month = int(expiring_month_str) if expiring_month_str else None
            expiring_year = int(expiring_year_str) if expiring_year_str else None
            
            result = CertificateController.get_certificates(
                page=page,
                page_size=page_size,
                status=status,
                country=country,
                issuer=issuer,
                search=search,
                encryption_type=encryption_type,
                has_vulnerabilities=has_vulnerabilities if has_vulnerabilities else None,
                expiring_month=expiring_month,
                expiring_year=expiring_year
            )
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CertificateDetailView(View):
    """
    GET /api/certificates/{id}
    Returns full details of a single certificate
    """
    def get(self, request, cert_id):
        try:
            certificate = CertificateController.get_certificate_by_id(cert_id)
            if certificate:
                return json_response(certificate)
            return json_response({'error': 'Certificate not found'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class UniqueFiltersView(View):
    """
    GET /api/unique-filters
    Returns unique values for filter dropdowns (issuers, countries, statuses, grades)
    """
    def get(self, request):
        try:
            filters = AnalyticsController.get_filter_options()
            return json_response(filters)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class EncryptionStrengthView(View):
    """
    GET /api/encryption-strength
    Returns encryption type distribution for charts
    """
    def get(self, request):
        try:
            data = AnalyticsController.get_encryption_distribution()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ValidityTrendsView(View):
    """
    GET /api/validity-trends
    Returns certificate expiration trends by month for line chart
    Query params: months_before (default 4), months_after (default 4)
    """
    def get(self, request):
        try:
            months_before = int(request.GET.get('months_before', 4))
            months_after = int(request.GET.get('months_after', 4))
            data = AnalyticsController.get_validity_trends(
                months_before=months_before,
                months_after=months_after
            )
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CAAnalyticsView(View):
    """
    GET /api/ca-analytics
    Returns Certificate Authority distribution for leaderboard
    Query params: limit (default 10)
    """
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            data = AnalyticsController.get_ca_leaderboard(limit=limit)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class GeographicDistributionView(View):
    """
    GET /api/geographic-distribution
    Returns certificate distribution by country
    Query params: limit (default 10)
    """
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            data = AnalyticsController.get_geographic_distribution(limit=limit)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class FutureRiskView(View):
    """
    GET /api/future-risk
    Returns predicted risk data
    """
    def get(self, request):
        try:
            data = AnalyticsController.get_future_risk()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VulnerabilitiesView(View):
    """
    GET /api/vulnerabilities
    Returns certificates with vulnerabilities (errors/warnings)
    Query params: page, page_size
    """
    def get(self, request):
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            
            # Get certificates and filter for those with vulnerabilities
            result = CertificateController.get_certificates(page=page, page_size=page_size)
            
            # Filter for certificates with vulnerabilities
            vuln_certs = [
                cert for cert in result['certificates']
                if cert['vulnerabilityCount']['errors'] > 0 or cert['vulnerabilityCount']['warnings'] > 0
            ]
            
            # Summary counts
            critical_count = sum(1 for c in vuln_certs if c['vulnerabilityCount']['errors'] > 0)
            warning_count = sum(1 for c in vuln_certs if c['vulnerabilityCount']['warnings'] > 0 and c['vulnerabilityCount']['errors'] == 0)
            
            return json_response({
                'certificates': vuln_certs,
                'summary': {
                    'critical': critical_count,
                    'warning': warning_count,
                    'total': len(vuln_certs)
                },
                'pagination': result['pagination']
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


# Keep legacy view for backwards compatibility
def hello_mongo_view(request):
    try:
        from .db import db
        collection = db['certificates']
        count = collection.count_documents({})
        return JsonResponse({
            'message': 'Connected to MongoDB successfully!',
            'database': 'latest-pk-domains',
            'collection': 'certificates',
            'documentCount': count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)