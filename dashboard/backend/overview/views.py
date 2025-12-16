from django.http import JsonResponse
from SSL_Dashboard.db_config import DBConnection
from .models import OverviewDataService, CertificateDetailService
from .serialization import OverviewSerializer
import logging

# Set up logging to see errors in Render console
logger = logging.getLogger(__name__)

def connect_db():
    """Establish MongoDB connection."""
    try:
        return DBConnection()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

def filter_params(request):
    """
    Extracts filtering parameters from the frontend request.
    Removes any empty values.
    """
    filters = {
        "status": request.GET.get("status"),
        "issuer": request.GET.get("issuer"),
        "country": request.GET.get("country"),
        "validation_level": request.GET.get("validation_level"),
    }
    return {k: v for k, v in filters.items() if v}

def overview_data(request):
    """
    Main analytics endpoint:
    - Summary counts
    - Trends chart data
    """
    try:
        db_conn = connect_db()
        overview_service = OverviewDataService(db_conn)

        filters = filter_params(request)

        summary = overview_service.get_summary(**filters)
        trends = overview_service.get_trends(**filters)

        data = OverviewSerializer.serialize_overview(summary)
        data["trends"] = trends

        return JsonResponse(data, safe=False)
    
    except Exception as e:
        logger.error(f"Error in overview_data: {e}")
        return JsonResponse({"error": "Internal Server Error", "details": str(e)}, status=500)

def certificate_list(request):
    """
    Paginated certificate list endpoint.
    """
    try:
        db_conn = connect_db()
        service = CertificateDetailService(db_conn)

        # Pagination with safe integer conversion
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))
        except ValueError:
            page = 1
            page_size = 20

        filters = filter_params(request)
        data = service.get_certificates(page=page, page_size=page_size, **filters)

        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error(f"Error in certificate_list: {e}")
        return JsonResponse({"error": "Internal Server Error", "details": str(e)}, status=500)

def certificate_warnings(request):
    """
    Paginated endpoint returning certificates along with their zlint warnings.
    """
    try:
        db_conn = connect_db()
        service = CertificateDetailService(db_conn)

        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))
        except ValueError:
            page = 1
            page_size = 20

        filters = filter_params(request)
        data = service.get_certificate_warnings(page=page, page_size=page_size, **filters)

        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error(f"Error in certificate_warnings: {e}")
        return JsonResponse({"error": "Internal Server Error", "details": str(e)}, status=500)