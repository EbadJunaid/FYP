from .db import MongoDBClient


class ScopeMiddleware:
    """Apply the requested logical certificate scope for each API request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        scope = request.GET.get('scope') or request.headers.get('X-Certificate-Scope')
        if scope is not None:
            MongoDBClient.set_current_scope(scope)
        return self.get_response(request)
