# holy_cross/middleware.py
from django.middleware.cache import FetchFromCacheMiddleware, UpdateCacheMiddleware

from admissions.utils import should_skip_cache


class SelectiveUpdateCacheMiddleware(UpdateCacheMiddleware):
    def process_response(self, request, response):
        if should_skip_cache(request):
            return response
        return super().process_response(request, response)


class SelectiveFetchFromCacheMiddleware(FetchFromCacheMiddleware):
    def process_request(self, request):
        if should_skip_cache(request):
            return None
        return super().process_request(request)
