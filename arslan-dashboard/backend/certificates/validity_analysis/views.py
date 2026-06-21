from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .controllers import ValidityAnalysisController

def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response


@method_decorator(csrf_exempt, name='dispatch')
class ValidityStatsView(View):
    """
    GET /api/validity-stats
    Returns validity statistics: avg duration, expiring counts, compliance rate
    """
    def get(self, request):
        try:
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
            result = ValidityAnalysisController.get_validity_distribution()
            return json_response(result)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class IssuanceTimelineView(View):
    """
    GET /api/trends/issuance-timeline
    Returns certificate issuance count by month
    Query params: months (default 12)
    """
    def get(self, request):
        try:
            months = int(request.GET.get('months', 12))
            data = ValidityAnalysisController.get_issuance_timeline(months=months)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
