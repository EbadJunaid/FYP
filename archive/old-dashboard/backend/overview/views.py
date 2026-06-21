from django.http import JsonResponse

from SSL_Dashboard.db_config import DBConnection
from .models import OverviewDataService, CertificateDetailService
from .serialization import OverviewSerializer


def connect_db():
    """Establish MongoDB connection."""
    return DBConnection()


def filter(request):
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

    db_conn = connect_db()
    overview_service = OverviewDataService(db_conn)

    filters = filter(request)

    summary = overview_service.get_summary(**filters)
    trends = overview_service.get_trends(**filters)

    data = OverviewSerializer.serialize_overview(summary)
    data["trends"] = trends

    return JsonResponse(data, safe=False)


def certificate_list(request):
    """
    Paginated certificate list endpoint.
    Returns refined, structured fields of each certificate.
    """

    db_conn = connect_db()
    service = CertificateDetailService(db_conn)

    # Pagination
    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1

    try:
        page_size = int(request.GET.get("page_size", 20))
    except ValueError:
        page_size = 20

    filters = filter(request)

    data = service.get_certificates(page=page, page_size=page_size, **filters)

    return JsonResponse(data, safe=False)



# def certificate_warnings(request):
#     """
#     Paginated endpoint returning certificates along with their zlint warnings.
#     Iterates through all lints and extracts those where result == 'warn'.
#     """

#     db_conn = connect_db()
#     service = CertificateDetailService(db_conn)

#     # Pagination
#     try:
#         page = int(request.GET.get("page", 1))
#     except ValueError:
#         page = 1

#     try:
#         page_size = int(request.GET.get("page_size", 20))
#     except ValueError:
#         page_size = 20

#     # Extract filters (status, issuer, country, etc.)
#     filters = filter(request)

#     # Fetch warning-based results
#     data = service.get_certificate_warnings(page=page, page_size=page_size, **filters)

#     return JsonResponse(data, safe=False)
