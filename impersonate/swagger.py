from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def create_impersonate(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'id': openapi.Schema(type=openapi.TYPE_INTEGER,
                                     description='ID of the employee whom you want to impersonate')
            },
            ['id']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": {"token": "03bc31076e8ff06317d3529b24d7e400e14f6ebe"},
                                                         "message": "User is impersonated"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized',
                  'response': {"message": "You don't have permission to impersonate this User"}},
            404: {'description': 'Not Found', 'response': {"message": "User does not exist"}}
        }
    )(view_func)

    return decorated_view


def impersonate_users(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 627, "employee_id": 2942, "name": "sumedha keshavabhatla",
                 "email": "sumedha.k@consultadd.com"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
