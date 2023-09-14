from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS, ERROR_MSG
from utils_app.utils import generate_swagger_auto_schema


def list_tracking(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'sort_by',
                'description': "The parameter by which you want to sort the data.",
                'type': openapi.TYPE_STRING
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1, "employee_id": 1000, "email": "product@consultadd.com", "employee_name": "Consultadd Admin",
                 "active_login": 1, "export_click": 0, "devices": [1]}], "total": 564}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def tracking_set_location(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'longitude': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Longitude of device."
                ),
                'latitude': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Latitude of device."
                ),
                'HTTP_X_ID_TOKEN': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Token"
                ),

            },
            ['longitude', 'latitude', 'HTTP_X_ID_TOKEN']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": "location added"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def tracking_get_locations(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'filter_json',
                'description': "To filter the data based on start and end date.",
                'type': openapi.TYPE_OBJECT
            }
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"display_name": "Home", "modified": "2023-09-14T10:12:13Z"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def tracking_get_export_info(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'filter_json',
                'description': "To filter the data based on start, end date and export_type.",
                'type': openapi.TYPE_OBJECT
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"date": "2023-09-14", "count": 1}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def tracking_device_list(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'emp_id',
                'description': "Employee ID of employee.",
                'type': openapi.TYPE_INTEGER
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [1]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def tracking_export_list(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": ["home"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view
