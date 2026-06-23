from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .controllers import SignatureHashController

def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response


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
            result = SignatureHashController.get_signature_stats()
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
            months = int(request.GET.get('months', 36))
            granularity = request.GET.get('granularity', 'quarterly')
            
            result = SignatureHashController.get_hash_trends(months=months, granularity=granularity)
            return json_response(result)
        except ValueError as e:
            return json_response({'error': f'Invalid parameter: {str(e)}'}, status=400)
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
            limit = int(request.GET.get('limit', 10))
            result = SignatureHashController.get_issuer_algorithm_matrix(limit=limit)
            return json_response(result)
        except ValueError as e:
            return json_response({'error': f'Invalid parameter: {str(e)}'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
