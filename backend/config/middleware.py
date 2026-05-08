import logging
import time

from django.db import connection, reset_queries

logger = logging.getLogger("apps.middleware")


class RequestLoggingMiddleware:
    """Logs request method, path, status, duration, and SQL query count."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        # Only count queries in DEBUG mode (django.db.reset_queries needs DEBUG=True)
        response = self.get_response(request)
        duration = (time.time() - start) * 1000

        query_count = len(connection.queries) if hasattr(connection, "queries") else 0
        log_level = logging.WARNING if query_count > 20 or duration > 500 else logging.DEBUG
        logger.log(
            log_level,
            "%s %s → %s (%.0fms, %d queries)",
            request.method,
            request.path,
            response.status_code,
            duration,
            query_count,
        )
        return response
