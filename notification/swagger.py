from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def create_fcm_token(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'fcm_token': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Device ID."
                ),

            },
            ['fcm_token']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"message": "Token Created"}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Already exists', 'response': {"message": "Token already exist"}}
        }
    )(view_func)

    return decorated_view


def list_emp_notify(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'model',
                'description': 'Name of parent or target content type.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 389679, "description": "Project Terminated :: Nisha Karki :: Synapse", "unread": False,
                 "timestamp": "2022-08-05T21:32:41.624766Z",
                 "target": {"id": 90, "sub_id": 90, "name": "consultant", "sub_name": "project"},
                 "avatar": "Nupur Malhotra"}], "total": 579, "unread": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def emp_notify_mark_as_read(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {'message': 'read'}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def emp_notify_mark_all_read(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {'message': 'read'}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def emp_notify_count(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"count": 5}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def emp_notify_push_notification(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'consultant_id',
                'description': 'ID of consultant.',
                'type': openapi.TYPE_INTEGER,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "done"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def emp_notify_remind_me_later(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'user_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of user."
                ),
                'types': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="For which models you want to create notification (interview, project, consultant).",
                    items=openapi.Items(type=openapi.TYPE_STRING)
                ),
            },
            ['user_id', 'types']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Notification snoozed for next 2 hours"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def emp_notify_notification_due(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"project": {"count": 0, "projects": []},
                                                                  "interview": {"count": 1, "interviews": [
                                                                      {"round": 2, "interview_id": 9193,
                                                                       "schedule": "2023-03-17T17:00:58Z",
                                                                       "consultant": {"name": "Mahima Sunmoriya"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {"client": "Morgan Stanley",
                                                                                      "vendor": "Genpact",
                                                                                      "job_title": "python_developer"}},
                                                                      {"round": 1, "interview_id": 9420,
                                                                       "schedule": "2023-04-19T12:30:00Z",
                                                                       "consultant": {"name": "Nandini Goswami"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {"client": "Corteva",
                                                                                      "vendor": "Paragon IT Professionals",
                                                                                      "job_title": "python_developer"}},
                                                                      {"round": 1, "interview_id": 9470,
                                                                       "schedule": "2023-05-31T16:00:00Z",
                                                                       "consultant": {"name": "Aishwarya Soma"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {"client": "Bimodal",
                                                                                      "vendor": "GrabTalent Advisors",
                                                                                      "job_title": "devops_engineer"}},
                                                                      {"round": 1, "interview_id": 9490,
                                                                       "schedule": "2023-05-08T14:00:00Z",
                                                                       "consultant": {"name": "Richa Mistry"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {
                                                                           "client": "The New York Times Wirecutter",
                                                                           "vendor": "The New York Times",
                                                                           "job_title": "devops_engineer"}},
                                                                      {"round": 1, "interview_id": 9507,
                                                                       "schedule": "2023-05-09T11:00:00Z",
                                                                       "consultant": {"name": "Richa Mistry"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {"client": "Ivedha",
                                                                                      "vendor": "iVedha Inc",
                                                                                      "job_title": "devops_engineer"}},
                                                                      {"round": 2, "interview_id": 9516,
                                                                       "schedule": "2023-05-15T14:00:23Z",
                                                                       "consultant": {"name": "Sirisha Veeram Reddy"},
                                                                       "supervisor_detail": {
                                                                           "supervisor_name": "Yashika Khatri",
                                                                           "call_given_by": "Interviewee"},
                                                                       "submission": {"client": "Bimodal",
                                                                                      "vendor": "BiModal Recruiting ",
                                                                                      "job_title": "python_developer"}}]},
                                                                  "update": {"count": 0, "updates": []}}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_con_notify(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"results": [
                {"id": 553093, "description": "Pratyush Solanki is updated as Marketer on Gyana Sahu",
                 "title": "Pratyush Solanki is updated as Marketer on Gyana Sahu", "deleted": False, "unread": True,
                 "timestamp": "2023-08-14T11:22:04.887923Z", "category": "info", "target_object_id": 578}],
                "total": 10}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_count(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"count": 4}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_mark_as_delete(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"result": [
                {"id": 553126, "description": "your projets updates were not given for last weeks", "deleted": False,
                 "unread": True, "timestamp": "2023-09-05T15:03:18.362760Z", "target_content_type__model": "consultant",
                 "target_object_id": 240}], "total": 1}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_mark_not_delete(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"result": [
                {"id": 553126, "description": "your projets updates were not given for last weeks", "deleted": False,
                 "unread": True, "timestamp": "2023-09-05T15:03:18.362760Z", "target_content_type__model": "consultant",
                 "target_object_id": 240}], "total": 1}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_mark_all_delete(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"result": "deleted"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_mark_as_read(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"result": [
                {"id": 553126, "description": "your projets updates were not given for last weeks", "deleted": False,
                 "unread": True, "timestamp": "2023-09-05T15:03:18.362760Z", "target_content_type__model": "consultant",
                 "target_object_id": 240}], "total": 1}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def con_notify_mark_all_read(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"result": "read"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view
