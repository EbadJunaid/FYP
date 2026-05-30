from django.http import JsonResponse,HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import csv
import json
from ..db import MongoDBClient
from .controllers import SharedApisController,GlobalFilterParams



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
            metrics = SharedApisController.get_global_health()
            return json_response(metrics)
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
            data = SharedApisController.get_validity_trends(
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
            
            data = SharedApisController.get_ca_leaderboard(limit=limit, global_filters=global_filters)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)



class GeographicDistributionView(View):
    """
    GET /api/geographic-distribution
    Returns certificate distribution by country
    Query params: limit, start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            
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
            
            data = SharedApisController.get_geographic_distribution(limit=limit, global_filters=global_filters)
            return json_response(data)
        except Exception as e:
            # print(f"Error in GeographicDistributionView: {e}")
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
            
            # Expiring date range filter (for weekly trends clicks)
            expiring_start = request.GET.get('expiring_start')
            expiring_end = request.GET.get('expiring_end')
            
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
            
            # Issued within days filter (for "Issued (30d)" card click)
            issued_within_days_str = request.GET.get('issued_within_days')
            issued_within_days = int(issued_within_days_str) if issued_within_days_str else None
            
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
            
            # SAN Analytics page specific filters
            san_tld = request.GET.get('san_tld')  # e.g., ".com", ".pk"
            san_type = request.GET.get('san_type')  # "wildcard" or "standard"
            san_count_min_str = request.GET.get('san_count_min')  # For SAN Count Distribution
            san_count_max_str = request.GET.get('san_count_max')
            san_count_min = int(san_count_min_str) if san_count_min_str else None
            san_count_max = int(san_count_max_str) if san_count_max_str else None
            
            # Shared Keys page specific filter
            shared_key = request.GET.get('shared_key', '').lower() == 'true'
            
            result = SharedApisController.get_certificates(
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
                issued_within_days=issued_within_days,
                signature_algorithm=signature_algorithm,
                weak_hash=weak_hash if weak_hash else None,
                self_signed=self_signed_filter if self_signed_filter else None,
                key_size=key_size,
                hash_type=hash_type,
                san_tld=san_tld,
                san_type=san_type,
                san_count_min=san_count_min,
                san_count_max=san_count_max,
                expiring_start=expiring_start,
                expiring_end=expiring_end,
                shared_key=shared_key if shared_key else None,
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
            certificate = SharedApisController.get_certificate_by_id(cert_id)
            if certificate:
                return json_response(certificate)
            return json_response({'error': 'Certificate not found'}, status=404)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class CurrentDatabaseView(View):
    
    def get(self, request):
        """GET /api/databases/current/ - Get current database configuration"""
        if request.method != 'GET':
            return json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            current_db = MongoDBClient.get_current_database()
            return json_response(current_db)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AvailableDatabasesView(View):
    
    def get(self, request):
        """GET /api/databases/available/ - Get all available databases"""
        if request.method != 'GET':
            return json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            databases = MongoDBClient.get_available_databases()
            return json_response(databases)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SwitchDatabaseView(View):

    def get(self, request):
        """POST /api/databases/switch/ - Switch to a different database"""
        if request.method != 'POST':
            return json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = json.loads(request.body)
            db_id = data.get('database_id')
            
            if not db_id:
                return json_response({'error': 'database_id is required'}, status=400)
            
            success = MongoDBClient.switch_database(db_id)
            
            if success:
                current_db = MongoDBClient.get_current_database()
                return json_response({
                    'success': True,
                    'message': f'Successfully switched to {current_db["name"]}',
                    'current_database': current_db
                })
            else:
                return json_response({'error': 'Invalid database_id'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
