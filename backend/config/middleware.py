import logging
import time

logger = logging.getLogger("apps.middleware")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = (time.time() - start) * 1000
        logger.debug(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        return response
