from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def retrieve_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'model', 'description': 'Name of model', 'type': openapi.TYPE_STRING, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 2049, "comment_text": "Commen",
                                                                   "user": {"id": 113, "employee_id": 2285,
                                                                            "email": "nihit.s@consultadd.com",
                                                                            "employee_name": "Nihit Kumar Singh",
                                                                            "team": "Ozrics (ELK / Devops)",
                                                                            "roles": ["marketer"], "gender": "male",
                                                                            "phone": "16823774092", "avatar": "avatar",
                                                                            "is_superuser": False,
                                                                            "technology": ["AWS"]},
                                                                   "parent_comment": None, "object_id": 75113,
                                                                   "tagged_user": [], "child_comment": [],
                                                                   "created": "2023-05-17T02:06:29.217820Z"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def create_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'model': openapi.Schema(type=openapi.TYPE_STRING, description='Model name'),
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of comment'),
                'comment_text': openapi.Schema(type=openapi.TYPE_STRING, description='Comment'),
                'parent_comment': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of parent comment'),
                'tagged_user': openapi.Schema(type=openapi.TYPE_ARRAY, description='ID of users who are tagged',
                                              items=openapi.Items(type=openapi.TYPE_INTEGER)),
            },
            [
                'model', 'id', 'comment_text', 'parent_comment'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Something went wrong. Please contact support",
                                                         "data": {"id": 2059, "comment_text": "test comment",
                                                                  "user": {"id": 998, "employee_id": 3096,
                                                                           "email": "v.s@c.com", "employee_name": "v c",
                                                                           "team": "Consultadd", "roles": ["engineer"],
                                                                           "gender": "male", "phone": "8484838484",
                                                                           "avatar": None, "is_superuser": False,
                                                                           "technology": None}, "parent_comment": 2058,
                                                                  "object_id": 949494, "tagged_user": [],
                                                                  "child_comment": [],
                                                                  "created": "2023-08-14T08:02:52.533007Z"}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view
