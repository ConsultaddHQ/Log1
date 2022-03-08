import logging

logger = logging.getLogger('address')


class AddressLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self.process_response(request, response)
        return response

    @staticmethod
    def process_response(request, response):
        address = request.META['REMOTE_ADDR']
        request_path = str(getattr(request, 'path', ''))
        method = str(getattr(request, 'method', '')).upper()
        if str(request.user) == "AnonymousUser":
            logger.info(f"{method} :: {address} :: {request_path} :: 1")
        else:
            if hasattr(request.user, "name"):
                logger.info(f"Consultant :: {method} :: {address} :: {request_path} :: {request.user.id} :: "
                            f"{request.user.name}")
            else:
                logger.info(f"Employee :: {method} :: {address} :: {request_path} :: {request.user.id} :: "
                            f"{request.user.employee_name}")
