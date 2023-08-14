from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def retrieve_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'model', 'description': 'Name of model', 'type': openapi.TYPE_STRING, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 130900, "object_id": 38136, "attachment_type": "timesheet", "file_name": "2020_yashjarad_1.png",
                 "type": {"name": "timesheet", "display_name": "Timesheet"}}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def attachment_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'obj_type': openapi.Schema(type=openapi.TYPE_STRING, description='Model name of object'),
                'object_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of object'),
                'attachment_type': openapi.Schema(type=openapi.TYPE_STRING, description='Attachment type of object'),
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='File to upload'),
            },
            [
                'obj_type', 'object_id', 'attachment_type', 'file'
            ],
        ],
        responses={
            201: {'description': 'Success'},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view