import logging
logger = logging.getLogger('address')


class AddressLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        address = request.META['REMOTE_ADDR']
        request_path = str(getattr(request, 'path', ''))
        method = str(getattr(request, 'method', '')).upper()
        logger.info(f"{method} :: {address} :: {request_path}")
