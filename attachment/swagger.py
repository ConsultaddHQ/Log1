from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def attachment_retrieve(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'obj_type', 'description': 'Model name of object', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'object_id', 'description': 'ID of object', 'type': openapi.TYPE_INTEGER, 'required': True},
            {'name': 'type', 'description': 'Attachment type of object', 'type': openapi.TYPE_STRING},
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


def attachment_delete(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'type', 'description': 'Model name of object', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'attachment_id', 'description': 'ID of attachment', 'type': openapi.TYPE_INTEGER,
             'required': True},
        ],
        responses={
            202: {'description': 'Success'},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def get_attachment_retrieve(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": "url", "file_type": "png"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def get_attachment_upload(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'obj_type': openapi.Schema(type=openapi.TYPE_STRING, description='Model name of object'),
                'object_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of object'),
                'file_name': openapi.Schema(type=openapi.TYPE_FILE, description='Name of file'),
            },
            [
                'obj_type', 'object_id', 'file_name'
            ],
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": {"url": "https://log1dev.s3.amazonaws.com/",
                                                                  "fields": {
                                                                      "key": "key",
                                                                      "x-amz-algorithm": "algorithm",
                                                                      "x-amz-credential": "credential",
                                                                      "x-amz-date": "date",
                                                                      "policy": "policy",
                                                                      "x-amz-signature": "signature"}},
                                                         "message": "Attachment uploaded"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view
