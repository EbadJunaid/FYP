from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .controllers import (SharedKeyController)

def json_response(data, status=200):
    """Helper to create JSON response with CORS headers"""
    response = JsonResponse(data, safe=False, status=status)
    return response


class SharedKeyStatsView(View):
    """
    GET /api/shared-keys/stats
    Returns shared key statistics for metric cards
    """
    def get(self, request):
        stats = SharedKeyController.get_stats()
        return json_response(stats)


class SharedKeyDistributionView(View):
    """
    GET /api/shared-keys/distribution
    Returns shared key group size distribution for histogram
    """
    def get(self, request):
        distribution = SharedKeyController.get_distribution()
        return json_response(distribution)


class SharedKeyByIssuerView(View):
    """
    GET /api/shared-keys/by-issuer
    Returns shared key certificates by issuer for bar chart
    Query params: limit
    """
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        data = SharedKeyController.get_by_issuer(limit)
        return json_response(data)


class SharedKeyTimelineView(View):
    """
    GET /api/shared-keys/timeline
    Returns timeline of certificates joining shared key groups
    Query params: months
    """
    def get(self, request):
        months = int(request.GET.get('months', 12))
        timeline = SharedKeyController.get_timeline(months)
        return json_response(timeline)


class SharedKeyHeatmapView(View):
    """
    GET /api/shared-keys/heatmap
    Returns issuer x key-type matrix for heatmap
    Query params: limit
    """
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        heatmap = SharedKeyController.get_heatmap(limit)
        return json_response(heatmap)

class SharedKeysListView(View):
    """
    GET /api/shared-keys/list
    Returns paginated list of shared key groups for table view
    Query params: page, page_size, sort_by, sort_order, risk_level, key_type, min_cert_count, issuer
    """
    def get(self, request):
        
        
        try:
            # Get query parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            sort_by = request.GET.get('sort_by', 'certificate_count')
            sort_order = request.GET.get('sort_order', 'desc')
            risk_level = request.GET.get('risk_level')
            key_type = request.GET.get('key_type')
            min_cert_count = request.GET.get('min_cert_count')
            issuer = request.GET.get('issuer')
            
            # Convert min_cert_count to int if provided
            if min_cert_count:
                min_cert_count = int(min_cert_count)
            
            # Get list from controller
            result = SharedKeyController.get_list(
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                risk_level=risk_level,
                key_type=key_type,
                min_cert_count=min_cert_count,
                issuer=issuer
            )
            
            return json_response({
                'success': True,
                'data': result
            })
        
        except ValueError as e:
            return json_response({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            return json_response({
                'success': False,
                'error': 'Failed to fetch shared keys list'
            }, status=500)


class SharedKeyDetailView(View):
    """
    GET /api/shared-keys/detail/<public_key_hash>
    Returns full details for a specific shared key group
    """
    def get(self, request, public_key_hash):
        
        try:
            result = SharedKeyController.get_detail(public_key_hash)
            
            return json_response({
                'success': True,
                'data': result
            })
        
        except ValueError as e:
            return json_response({
                'success': False,
                'error': str(e)
            }, status=404)
        except Exception as e:
            return json_response({
                'success': False,
                'error': 'Failed to fetch shared key details'
            }, status=500)