from .controllers import OverviewController
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from ..shared_apis.controllers import GlobalFilterParams


def json_response(data, status=200):
    return JsonResponse(data, safe=False, status=status)



@method_decorator(csrf_exempt, name='dispatch')
class EncryptionStrengthView(View):
    """
    GET /api/encryption-strength
    Returns encryption type distribution for charts
    Query params: start_date, end_date, countries, issuers, statuses, validation_levels
    """
    def get(self, request):
        try:
            
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
            
            data = OverviewController.get_encryption_distribution(global_filters=global_filters)
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
                data = OverviewController.get_future_risk()
                return json_response(data)
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
                filters = OverviewController.get_filter_options()
                return json_response(filters)
            except Exception as e:
                return json_response({'error': str(e)}, status=500)
