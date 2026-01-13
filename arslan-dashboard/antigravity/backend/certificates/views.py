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
    AnalyticsController,
    NotificationController
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


@method_decorator(csrf_exempt, name='dispatch')
class CertificateDownloadView(View):
    """
    GET /api/certificates/download
    Streams CSV download of certificates with optional filters
    Query params: status, country, issuer, search, encryption_type, has_vulnerabilities, expiring_month, expiring_year
    Handles millions of records via streaming without memory issues
    """
    def get(self, request):
        from django.http import StreamingHttpResponse
        import csv
        from io import StringIO
        from .models import CertificateModel
        from datetime import datetime, timezone, timedelta
        
        # Get filter params
        status = request.GET.get('status')
        country = request.GET.get('country')
        issuer = request.GET.get('issuer')
        search = request.GET.get('search')
        encryption_type = request.GET.get('encryption_type')
        has_vulnerabilities = request.GET.get('has_vulnerabilities', '').lower() == 'true'
        expiring_month_str = request.GET.get('expiring_month')
        expiring_year_str = request.GET.get('expiring_year')
        expiring_month = int(expiring_month_str) if expiring_month_str else None
        expiring_year = int(expiring_year_str) if expiring_year_str else None
        
        # Generate filename based on filter
        filename = 'certificates'
        if status:
            filename = f'{status.lower()}_certificates'
        elif issuer:
            safe_issuer = issuer.replace(' ', '_').replace("'", '')[:20]
            filename = f'{safe_issuer}_certificates'
        elif country:
            filename = f'{country.lower()}_certificates'
        
        response = StreamingHttpResponse(
            self._generate_csv(
                status=status,
                country=country,
                issuer=issuer,
                search=search,
                encryption_type=encryption_type,
                has_vulnerabilities=has_vulnerabilities if has_vulnerabilities else None,
                expiring_month=expiring_month,
                expiring_year=expiring_year
            ),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        response['Cache-Control'] = 'no-cache'
        return response
    
    def _generate_csv(self, **filters):
        """Generator for streaming CSV rows - handles millions without memory issues"""
        from .models import CertificateModel
        from datetime import datetime, timezone, timedelta
        from calendar import monthrange
        import csv
        from io import StringIO
        
        # Yield header row
        yield self._csv_row([
            'Domain', 'Start Date', 'End Date', 'SSL Grade', 
            'Encryption', 'Issuer', 'Country', 'Status', 'Vulnerabilities'
        ])
        
        # Build query (reuse logic from get_all)
        query = {}
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        if filters.get('search'):
            search = filters['search']
            query['$or'] = [
                {'parsed.subject.common_name': {'$regex': search, '$options': 'i'}},
                {'domain': {'$regex': search, '$options': 'i'}}
            ]
        
        if filters.get('issuer'):
            issuer = filters['issuer']
            if issuer.lower() == 'others':
                # Get top 10 CAs and exclude them
                top_ca_pipeline = [
                    {'$project': {'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}}},
                    {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
                    {'$group': {'_id': '$issuer_org', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                top_cas = [r['_id'] for r in CertificateModel.collection.aggregate(top_ca_pipeline)]
                query['$and'] = query.get('$and', [])
                query['$and'].append({
                    '$or': [
                        {'parsed.issuer.organization': {'$nin': top_cas}},
                        {'parsed.issuer.organization': {'$exists': False}}
                    ]
                })
            else:
                query['parsed.issuer.organization'] = {'$regex': issuer, '$options': 'i'}
        
        if filters.get('status'):
            status_upper = filters['status'].upper()
            if status_upper == 'EXPIRED':
                query['parsed.validity.end'] = {'$lt': now}
            elif status_upper == 'EXPIRING_SOON':
                query['parsed.validity.end'] = {'$gte': now, '$lte': now_plus_30}
            elif status_upper == 'VALID':
                query['parsed.validity.end'] = {'$gt': now}
        
        if filters.get('encryption_type'):
            parts = filters['encryption_type'].split()
            if len(parts) >= 1:
                algo_name = parts[0]
                query['parsed.subject_key_info.key_algorithm.name'] = algo_name
                if len(parts) >= 2:
                    try:
                        key_length = int(parts[1])
                        if algo_name.upper() == 'RSA':
                            query['parsed.subject_key_info.rsa_public_key.length'] = key_length
                        elif algo_name.upper() in ['ECDSA', 'EC']:
                            query['parsed.subject_key_info.ecdsa_public_key.length'] = key_length
                    except ValueError:
                        pass
        
        if filters.get('expiring_month') and filters.get('expiring_year'):
            _, last_day = monthrange(filters['expiring_year'], filters['expiring_month'])
            month_start = f"{filters['expiring_year']}-{filters['expiring_month']:02d}-01T00:00:00Z"
            month_end = f"{filters['expiring_year']}-{filters['expiring_month']:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.end'] = {'$gte': month_start, '$lte': month_end}
        
        if filters.get('has_vulnerabilities'):
            query['zlint.errors_present'] = True
        
        # Stream data in batches (batch_size for MongoDB cursor)
        cursor = CertificateModel.collection.find(query).batch_size(1000)
        
        for doc in cursor:
            cert = CertificateModel.serialize_certificate(doc)
            
            # Apply country filter after serialization (TLD-based)
            if filters.get('country') and cert.get('country') != filters['country']:
                continue
            
            yield self._csv_row([
                cert.get('domain', 'N/A'),
                cert.get('validFrom', 'N/A'),
                cert.get('validTo', 'N/A'),
                cert.get('sslGrade', 'N/A'),
                cert.get('encryptionType', 'N/A'),
                cert.get('issuer', 'N/A'),
                cert.get('country', 'N/A'),
                cert.get('status', 'N/A'),
                cert.get('vulnerabilityCount', 0)
            ])
    
    def _csv_row(self, row):
        """Convert row to CSV string"""
        from io import StringIO
        import csv
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(row)
        return output.getvalue()


@method_decorator(csrf_exempt, name='dispatch')
class NotificationView(View):
    """
    GET /api/notifications
    Returns real-time notifications based on certificate status
    (expiring soon, vulnerabilities, weak encryption, etc.)
    """
    def get(self, request):
        try:
            result = NotificationController.get_notifications()
            return json_response(result)
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