from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def list_city(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'Name of city.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'country',
                'description': 'Name of country.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"id": 23409, "name": "Abingdon", "state": "MD", "country": "USA"},
                         {"id": 23410, "name": "Abingdon", "state": "IL", "country": "USA"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def city_country(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'city',
                'description': 'Name of city with state.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": "USA"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_choice(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'field',
                'description': 'Name of model field.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'model',
                'description': 'Name of model.',
                'type': openapi.TYPE_STRING
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 217, "name": ".NET", "display_name": ".NET", "field": "technology",
                 "content_type__model": "user"},
                {"id": 218, "name": "C#", "display_name": "C-Sharp", "field": "technology",
                 "content_type__model": "user"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_choice(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'model': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of model."
                ),
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of choice."
                ),
                'field': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of field."
                ),
                'display_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Display name of choice."
                ),

            },
            ['model', 'name', 'field', 'display_name']
        ],
        responses={
            201: {'description': 'Success', 'response': {'message': 'Choice Created'}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def create_util(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': 'API Key.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": "data"}},
            400: {'description': 'Bad Request'},
            401: {'description': 'API key error'},
        }
    )(view_func)

    return decorated_view


def utility_get_technology(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": ["Hadoop", "Legacy Modernisation", ".NET", "C#", "Other"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def utility_add_technology(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'technology': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of technology."
                )
            },
            ['technology']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "updated technologies"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view
