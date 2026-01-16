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
    Query params: page, page_size, status, country, issuer, search, encryption_type, 
                  has_vulnerabilities, expiring_month, expiring_year, expiring_days, validity_bucket,
                  start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            from .controllers import GlobalFilterParams
            
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
            
            # Expiring days filter (for 30/60/90 day specific filtering)
            expiring_days_str = request.GET.get('expiring_days')
            expiring_days = int(expiring_days_str) if expiring_days_str else None
            
            # Validity bucket filter (for distribution card clicks)
            validity_bucket = request.GET.get('validity_bucket')  # e.g., "0-90", "90-365", "365-730", "730+"
            
            # Global filter params - date range
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Global filter params - multi-select arrays (comma-separated)
            countries_str = request.GET.get('countries', '')
            issuers_str = request.GET.get('issuers', '')
            statuses_str = request.GET.get('statuses', '')
            validation_levels_str = request.GET.get('validation_levels', '')
            
            # Issued month/year filter (for issuance timeline clicks)
            issued_month_str = request.GET.get('issued_month')
            issued_year_str = request.GET.get('issued_year')
            issued_month = int(issued_month_str) if issued_month_str else None
            issued_year = int(issued_year_str) if issued_year_str else None
            
            countries = [c.strip() for c in countries_str.split(',') if c.strip()] if countries_str else None
            issuers_list = [i.strip() for i in issuers_str.split(',') if i.strip()] if issuers_str else None
            statuses_list = [s.strip() for s in statuses_str.split(',') if s.strip()] if statuses_str else None
            validation_levels = [v.strip() for v in validation_levels_str.split(',') if v.strip()] if validation_levels_str else None
            
            # Build global filters if any filter params provided
            global_filters = None
            if start_date or end_date or countries or issuers_list or statuses_list or validation_levels:
                global_filters = GlobalFilterParams(
                    start_date=start_date,
                    end_date=end_date,
                    countries=countries,
                    issuers=issuers_list,
                    statuses=statuses_list,
                    validation_levels=validation_levels
                )
            
            # Signature/Hash page specific filters
            signature_algorithm = request.GET.get('signature_algorithm')
            weak_hash = request.GET.get('weak_hash', '').lower() == 'true'
            self_signed_filter = request.GET.get('self_signed', '').lower() == 'true'
            key_size_str = request.GET.get('key_size')
            key_size = int(key_size_str) if key_size_str else None
            hash_type = request.GET.get('hash_type')
            
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
                expiring_year=expiring_year,
                expiring_days=expiring_days,
                validity_bucket=validity_bucket,
                issued_month=issued_month,
                issued_year=issued_year,
                signature_algorithm=signature_algorithm,
                weak_hash=weak_hash if weak_hash else None,
                self_signed=self_signed_filter if self_signed_filter else None,
                key_size=key_size,
                hash_type=hash_type,
                global_filters=global_filters
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
    Query params: start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            from .controllers import GlobalFilterParams
            
            # Parse global filter params - date range
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Parse multi-select arrays (comma-separated)
            countries_str = request.GET.get('countries', '')
            issuers_str = request.GET.get('issuers', '')
            statuses_str = request.GET.get('statuses', '')
            validation_levels_str = request.GET.get('validation_levels', '')
            
            countries = [c.strip() for c in countries_str.split(',') if c.strip()] if countries_str else None
            issuers_list = [i.strip() for i in issuers_str.split(',') if i.strip()] if issuers_str else None
            statuses_list = [s.strip() for s in statuses_str.split(',') if s.strip()] if statuses_str else None
            validation_levels = [v.strip() for v in validation_levels_str.split(',') if v.strip()] if validation_levels_str else None
            
            global_filters = None
            if start_date or end_date or countries or issuers_list or statuses_list or validation_levels:
                global_filters = GlobalFilterParams(
                    start_date=start_date,
                    end_date=end_date,
                    countries=countries,
                    issuers=issuers_list,
                    statuses=statuses_list,
                    validation_levels=validation_levels
                )
            
            data = AnalyticsController.get_encryption_distribution(global_filters=global_filters)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ValidityTrendsView(View):
    """
    GET /api/validity-trends
    Returns certificate expiration trends by month or week for line chart
    Query params: months_before (default 4), months_after (default 4), granularity ('monthly' or 'weekly')
    """
    def get(self, request):
        try:
            months_before = int(request.GET.get('months_before', 4))
            months_after = int(request.GET.get('months_after', 4))
            granularity = request.GET.get('granularity', 'monthly')
            data = AnalyticsController.get_validity_trends(
                months_before=months_before,
                months_after=months_after,
                granularity=granularity
            )
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CAAnalyticsView(View):
    """
    GET /api/ca-analytics
    Returns Certificate Authority distribution for leaderboard
    Query params: limit, start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            from .controllers import GlobalFilterParams
            
            limit = int(request.GET.get('limit', 10))
            
            # Parse global filter params - date range
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Parse multi-select arrays (comma-separated)
            countries_str = request.GET.get('countries', '')
            issuers_str = request.GET.get('issuers', '')
            statuses_str = request.GET.get('statuses', '')
            validation_levels_str = request.GET.get('validation_levels', '')
            
            countries = [c.strip() for c in countries_str.split(',') if c.strip()] if countries_str else None
            issuers_list = [i.strip() for i in issuers_str.split(',') if i.strip()] if issuers_str else None
            statuses_list = [s.strip() for s in statuses_str.split(',') if s.strip()] if statuses_str else None
            validation_levels = [v.strip() for v in validation_levels_str.split(',') if v.strip()] if validation_levels_str else None
            
            global_filters = None
            if start_date or end_date or countries or issuers_list or statuses_list or validation_levels:
                global_filters = GlobalFilterParams(
                    start_date=start_date,
                    end_date=end_date,
                    countries=countries,
                    issuers=issuers_list,
                    statuses=statuses_list,
                    validation_levels=validation_levels
                )
            
            data = AnalyticsController.get_ca_leaderboard(limit=limit, global_filters=global_filters)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class GeographicDistributionView(View):
    """
    GET /api/geographic-distribution
    Returns certificate distribution by country
    Query params: limit, start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            from .controllers import GlobalFilterParams
            
            limit = int(request.GET.get('limit', 10))
            
            # Parse global filter params - date range
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Parse multi-select arrays (comma-separated)
            countries_str = request.GET.get('countries', '')
            issuers_str = request.GET.get('issuers', '')
            statuses_str = request.GET.get('statuses', '')
            validation_levels_str = request.GET.get('validation_levels', '')
            
            countries = [c.strip() for c in countries_str.split(',') if c.strip()] if countries_str else None
            issuers_list = [i.strip() for i in issuers_str.split(',') if i.strip()] if issuers_str else None
            statuses_list = [s.strip() for s in statuses_str.split(',') if s.strip()] if statuses_str else None
            validation_levels = [v.strip() for v in validation_levels_str.split(',') if v.strip()] if validation_levels_str else None
            
            global_filters = None
            if start_date or end_date or countries or issuers_list or statuses_list or validation_levels:
                global_filters = GlobalFilterParams(
                    start_date=start_date,
                    end_date=end_date,
                    countries=countries,
                    issuers=issuers_list,
                    statuses=statuses_list,
                    validation_levels=validation_levels
                )
            
            data = AnalyticsController.get_geographic_distribution(limit=limit, global_filters=global_filters)
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
    Query params: status, country, issuer, search, encryption_type, has_vulnerabilities, 
                  expiring_month, expiring_year, issued_month, issued_year,
                  weak_hash, self_signed, signature_algorithm, hash_type, validity_bucket, expiring_days
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
        
        # Expiring/issued date filters
        expiring_month_str = request.GET.get('expiring_month')
        expiring_year_str = request.GET.get('expiring_year')
        expiring_month = int(expiring_month_str) if expiring_month_str else None
        expiring_year = int(expiring_year_str) if expiring_year_str else None
        
        issued_month_str = request.GET.get('issued_month')
        issued_year_str = request.GET.get('issued_year')
        issued_month = int(issued_month_str) if issued_month_str else None
        issued_year = int(issued_year_str) if issued_year_str else None
        
        # Signature page specific filters
        weak_hash = request.GET.get('weak_hash', '').lower() == 'true'
        self_signed = request.GET.get('self_signed', '').lower() == 'true'
        signature_algorithm = request.GET.get('signature_algorithm')
        hash_type = request.GET.get('hash_type')
        validity_bucket = request.GET.get('validity_bucket')
        expiring_days_str = request.GET.get('expiring_days')
        expiring_days = int(expiring_days_str) if expiring_days_str else None
        
        # Generate filename based on filter
        filename = 'certificates'
        if status:
            filename = f'{status.lower()}_certificates'
        elif weak_hash:
            filename = 'weak_hash_certificates'
        elif self_signed:
            filename = 'self_signed_certificates'
        elif signature_algorithm:
            safe_algo = signature_algorithm.replace('-', '_')[:20]
            filename = f'{safe_algo}_certificates'
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
                expiring_year=expiring_year,
                issued_month=issued_month,
                issued_year=issued_year,
                weak_hash=weak_hash if weak_hash else None,
                self_signed=self_signed if self_signed else None,
                signature_algorithm=signature_algorithm,
                hash_type=hash_type,
                validity_bucket=validity_bucket,
                expiring_days=expiring_days
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
        
        # Signature page specific filters
        
        # Filter by issued month/year
        if filters.get('issued_month') and filters.get('issued_year'):
            _, last_day = monthrange(filters['issued_year'], filters['issued_month'])
            month_start = f"{filters['issued_year']}-{filters['issued_month']:02d}-01T00:00:00Z"
            month_end = f"{filters['issued_year']}-{filters['issued_month']:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.start'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by weak hash (SHA-1, MD5)
        if filters.get('weak_hash'):
            if '$or' not in query:
                query['$or'] = [
                    {'parsed.signature_algorithm.name': {'$regex': '^SHA1|^SHA-1', '$options': 'i'}},
                    {'parsed.signature_algorithm.name': {'$regex': '^MD5', '$options': 'i'}}
                ]
        
        # Filter by self-signed
        if filters.get('self_signed'):
            query['parsed.signature.self_signed'] = True
        
        # Filter by exact signature algorithm (e.g., "SHA256-RSA")
        if filters.get('signature_algorithm'):
            query['parsed.signature_algorithm.name'] = filters['signature_algorithm']
        
        # Filter by hash type (e.g., "SHA-256")
        if filters.get('hash_type'):
            hash_patterns = {
                'SHA-256': '^SHA256',
                'SHA-384': '^SHA384',
                'SHA-512': '^SHA512',
                'SHA-1': '^SHA1|^SHA-1',
                'MD5': '^MD5'
            }
            pattern = hash_patterns.get(filters['hash_type'], f"^{filters['hash_type'].replace('-', '')}")
            query['parsed.signature_algorithm.name'] = {'$regex': pattern, '$options': 'i'}
        
        # Filter by validity bucket (duration in days)
        if filters.get('validity_bucket'):
            bucket_ranges = {
                '0-90': (0, 90),
                '90-365': (90, 365),
                '365-730': (365, 730),
                '730+': (730, 9999)
            }
            if filters['validity_bucket'] in bucket_ranges:
                min_days, max_days = bucket_ranges[filters['validity_bucket']]
                min_seconds = min_days * 86400
                max_seconds = max_days * 86400
                query['parsed.validity.length'] = {'$gte': min_seconds, '$lt': max_seconds}
        
        # Filter by expiring days
        if filters.get('expiring_days'):
            target_date = (datetime.now(timezone.utc) + timedelta(days=filters['expiring_days'])).strftime('%Y-%m-%dT%H:%M:%SZ')
            query['parsed.validity.end'] = {
                '$gt': now,  # Not yet expired
                '$lte': target_date  # Within expiring_days window
            }
        
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
class ValidityStatsView(View):
    """
    GET /api/validity-stats
    Returns validity statistics: avg duration, expiring counts, compliance rate
    """
    def get(self, request):
        try:
            from .controllers import ValidityAnalysisController
            result = ValidityAnalysisController.get_validity_stats()
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ValidityDistributionView(View):
    """
    GET /api/validity-distribution
    Returns validity period distribution by buckets
    """
    def get(self, request):
        try:
            from .controllers import ValidityAnalysisController
            result = ValidityAnalysisController.get_validity_distribution()
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class IssuanceTimelineView(View):
    """
    GET /api/issuance-timeline
    Returns certificate issuance and expiration timeline by month
    """
    def get(self, request):
        try:
            from .controllers import ValidityAnalysisController
            result = ValidityAnalysisController.get_issuance_timeline()
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


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


# ----- New views for Signature and Hashes page -----

@method_decorator(csrf_exempt, name='dispatch')
class SignatureStatsView(View):
    """
    GET /api/signature-stats
    Returns comprehensive signature and hash statistics.
    Includes algorithm distribution, hash distribution, key sizes, compliance rate, strength score.
    Cached for 5 minutes.
    """
    def get(self, request):
        try:
            from .models import CertificateModel
            from .cache_service import cache
            
            # Check cache first
            cache_key = 'signature_stats'
            cached = cache.get(cache_key, {})
            if cached:
                return json_response(cached)
            
            # Get fresh data from model
            result = CertificateModel.get_signature_stats()
            
            # Cache for 5 minutes
            cache.set(cache_key, {}, result, ttl=300)
            
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class HashTrendsView(View):
    """
    GET /api/hash-trends
    Returns hash algorithm adoption trends over time.
    Query params: months (default 36), granularity ('quarterly' or 'yearly')
    Cached for 10 minutes.
    """
    def get(self, request):
        try:
            from .models import CertificateModel
            from .cache_service import cache
            
            months = int(request.GET.get('months', 36))
            granularity = request.GET.get('granularity', 'quarterly')
            
            # Validate granularity
            if granularity not in ['quarterly', 'yearly']:
                granularity = 'quarterly'
            
            # Check cache first
            cache_params = {'months': months, 'granularity': granularity}
            cached = cache.get('hash_trends', cache_params)
            if cached:
                return json_response(cached)
            
            # Get fresh data from model
            result = CertificateModel.get_hash_trends(months=months, granularity=granularity)
            
            # Cache for 10 minutes
            cache.set('hash_trends', cache_params, result, ttl=600)
            
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class IssuerAlgorithmMatrixView(View):
    """
    GET /api/issuer-algorithm-matrix
    Returns matrix of issuer x algorithm combinations with counts.
    Cached for 10 minutes.
    """
    def get(self, request):
        try:
            from .models import CertificateModel
            from .cache_service import cache
            
            limit = int(request.GET.get('limit', 10))
            
            # Check cache first
            cache_params = {'limit': limit}
            cached = cache.get('issuer_matrix', cache_params)
            if cached:
                return json_response(cached)
            
            # Get fresh data from model
            result = CertificateModel.get_issuer_algorithm_matrix(limit=limit)
            
            # Cache for 10 minutes
            cache.set('issuer_matrix', cache_params, result, ttl=600)
            
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CertificateExportView(View):
    """
    GET /api/certificates/export
    Export certificates as CSV with optional filters.
    Uses the same filters as CertificateListView to ensure filtered downloads.
    """
    def get(self, request):
        try:
            import csv
            from django.http import HttpResponse
            from .models import CertificateModel
            
            # Get filter parameters (same as CertificateListView)
            status = request.GET.get('status')
            country = request.GET.get('country')
            issuer = request.GET.get('issuer')
            search = request.GET.get('search')
            encryption_type = request.GET.get('encryption_type')
            
            # Signature/Hash page specific filters
            signature_algorithm = request.GET.get('signature_algorithm')
            weak_hash = request.GET.get('weak_hash', '').lower() == 'true'
            self_signed = request.GET.get('self_signed', '').lower() == 'true'
            key_size_str = request.GET.get('key_size')
            key_size = int(key_size_str) if key_size_str else None
            hash_type = request.GET.get('hash_type')
            
            # Build query with filters (without pagination for export)
            result = CertificateModel.get_all(
                page=1,
                page_size=10000,  # Get up to 10k records for export
                status=status,
                country=country,
                issuer=issuer,
                search=search,
                encryption_type=encryption_type,
                signature_algorithm=signature_algorithm,
                weak_hash=weak_hash if weak_hash else None,
                self_signed=self_signed if self_signed else None,
                key_size=key_size,
                hash_type=hash_type
            )
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="certificates.csv"'
            
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'Domain', 'Issuer', 'Status', 'Valid From', 'Valid To',
                'Encryption Type', 'Signature Algorithm', 'Key Size',
                'Country', 'Grade', 'Self-Signed'
            ])
            
            # Write data rows
            for cert in result.get('certificates', []):
                writer.writerow([
                    cert.get('domain', ''),
                    cert.get('issuer', ''),
                    cert.get('status', ''),
                    cert.get('validFrom', ''),
                    cert.get('validTo', ''),
                    cert.get('encryptionType', ''),
                    cert.get('signatureAlgorithm', ''),
                    cert.get('keySize', ''),
                    cert.get('country', ''),
                    cert.get('grade', ''),
                    cert.get('selfSigned', False)
                ])
            
            return response
        except Exception as e:
            return json_response({'error': str(e)}, status=500)