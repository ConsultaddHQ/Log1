import random
from importlib import import_module

from django.conf import settings


def get_token_generator():
    token_class = RandomStringTokenGenerator
    options = {}

    DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG = getattr(settings, 'DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG', None)

    if DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG:
        if "CLASS" in DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG:
            class_path_name = DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG["CLASS"]
            module_name, class_name = class_path_name.rsplit('.', 1)

            mod = import_module(module_name)
            token_class = getattr(mod, class_name)

        if "OPTIONS" in DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG:
            options = DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG["OPTIONS"]

    return token_class(**options)


class BaseTokenGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate_token(self, *args, **kwargs):
        raise NotImplementedError


class RandomStringTokenGenerator(BaseTokenGenerator):

    def generate_token(self, *args, **kwargs):
        return random.SystemRandom().randint(100000, 999999)
