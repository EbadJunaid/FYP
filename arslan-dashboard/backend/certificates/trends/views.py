from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .controllers import TrendsController

def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response




@method_decorator(csrf_exempt, name='dispatch')
class TrendsStatsView(View):
    """
    GET /api/trends/stats
    Returns trend statistics for metric cards
    """
    def get(self, request):
        try:
            data = TrendsController.get_trends_stats()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class ExpirationForecastView(View):
    """
    GET /api/trends/expiration-forecast
    Returns certificate expiration count by month
    Query params: months (default 12)
    """
    def get(self, request):
        try:
            months = int(request.GET.get('months', 12))
            data = TrendsController.get_expiration_forecast(months=months)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AlgorithmAdoptionView(View):
    """
    GET /api/trends/algorithm-adoption
    Returns algorithm distribution over time
    Query params: months (default 12)
    """
    def get(self, request):
        try:
            months = int(request.GET.get('months', 12))
            data = TrendsController.get_algorithm_adoption(months=months)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ValidationLevelTrendsView(View):
    """
    GET /api/trends/validation-levels
    Returns validation level (DV/OV/EV) distribution over time
    Query params: months (default 12)
    """
    def get(self, request):
        try:
            months = int(request.GET.get('months', 12))
            data = TrendsController.get_validation_level_trends(months=months)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class KeySizeTimelineView(View):
    """
    GET /api/trends/key-size-timeline
    Returns key size distribution over time for animated visualization
    Query params: months (default 12)
    """
    def get(self, request):
        try:
            months = int(request.GET.get('months', 12))
            data = TrendsController.get_key_size_timeline(months=months)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
