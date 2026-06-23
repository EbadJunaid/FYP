from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .controllers import (SANAnalyticsController)

def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response

@method_decorator(csrf_exempt, name='dispatch')
class SANStatsView(View):
    """
    GET /api/san-stats
    Returns SAN statistics for metric cards
    """
    def get(self, request):
        try:
            data = SANAnalyticsController.get_san_stats()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SANDistributionView(View):
    """
    GET /api/san-distribution
    Returns SAN count distribution (histogram buckets)
    """
    def get(self, request):
        try:
            data = SANAnalyticsController.get_san_distribution()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SANTLDBreakdownView(View):
    """
    GET /api/san-tld-breakdown
    Returns top TLDs from SAN entries
    Query params: limit
    """
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 15))
            data = SANAnalyticsController.get_san_tld_breakdown(limit=limit)
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SANWildcardBreakdownView(View):
    """
    GET /api/san-wildcard-breakdown
    Returns wildcard vs standard SAN breakdown
    """
    def get(self, request):
        try:
            data = SANAnalyticsController.get_san_wildcard_breakdown()
            return json_response(data)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SANFilteredCertsView(View):
    """
    GET /api/san-filtered-certs?filter_type=wildcard&page=1&page_size=50
    GET /api/san-filtered-certs?filter_type=san-count&filter_value=50+&page=1
    GET /api/san-filtered-certs?filter_type=tld&filter_value=.com&page=1
    
    Returns filtered certificates from pre-computed collections (fast!)
    """
    def get(self, request):
        try:
           
            filter_type = request.GET.get('filter_type', 'wildcard')
            filter_value = request.GET.get('filter_value', None)
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 50))
            
            data = SANAnalyticsController.get_san_filtered_certs(
                filter_type=filter_type,
                filter_value=filter_value,
                page=page,
                page_size=page_size
            )
            return json_response(data)
        except ValueError as e:
            return json_response({'error': str(e)}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
