from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .controllers import CAAnalyticsController


def json_response(data, status=200):
    return JsonResponse(data, safe=False, status=status)


@method_decorator(csrf_exempt, name='dispatch')
class CAStatsView(View):
    def get(self, request):
        try:
            data = CAAnalyticsController.get_ca_stats()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class IssuerValidationMatrixView(View):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            data = CAAnalyticsController.get_issuer_validation_matrix(limit=limit)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
