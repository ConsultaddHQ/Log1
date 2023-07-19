from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def list_dashboard_data(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_for', 'description': "Filter for 'my' or 'team'", 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'Team name', 'type': openapi.TYPE_STRING},
            {'name': 'filter_by', 'description': 'Find data of particular time interval', 'type': openapi.TYPE_STRING},
            {'name': 'start_year', 'description': 'Find data from start year', 'type': openapi.TYPE_STRING},
            {'name': 'end_year', 'description': 'Find data upto custom end year', 'type': openapi.TYPE_STRING},
            {'name': 'result_count', 'description': 'Find first N records of Recent Offers, Upcoming Joining,'
                                                    'Upcoming Interviews (default 5)', 'type': openapi.TYPE_INTEGER},
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"new_offers": [], "joining": [], "interviews": []},
                               "count": {"total_offers": 1, "offer": 1, "submission": 5, "on_project": 0, "ba_bench": 0,
                                         "dev_bench": 9, "interview": 9},
                               "offer_count": [{"name": "new", "count": 1}, {"name": "joined", "count": 0},
                                               {"name": "received", "count": 0}, {"name": "extended", "count": 0},
                                               {"name": "complete", "count": 0}, {"name": "cancelled", "count": 0},
                                               {"name": "terminated", "count": 0}, {"name": "on_boarded", "count": 0},
                                               {"name": "not_joined", "count": 0}]}
                  },
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def marketing_performance(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_for', 'description': "Filter for 'my' or 'team' or 'all'", 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'Team name', 'type': openapi.TYPE_STRING},
            {'name': 'filter_by', 'description': 'Find data of a particular time interval',
             'type': openapi.TYPE_STRING},
            {'name': 'start_year', 'description': 'Find data from start year', 'type': openapi.TYPE_STRING},
            {'name': 'end_year', 'description': 'Find data up to a custom end year', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": {"joined_count": 0, "joined_percent": 0,
                                                                  "conversions": {"offers": 25, "joining": 0,
                                                                                  "interview": 175,
                                                                                  "count": {"offer_count": 1,
                                                                                            "joining_count": 0,
                                                                                            "interview_count": 7,
                                                                                            "submission_count": 4}}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def dashboard_history(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_for', 'description': "Filter for 'my' or 'team' or 'all'", 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'Team name', 'type': openapi.TYPE_STRING},
            {'name': 'filter_by', 'description': 'Find data of a particular time interval',
             'type': openapi.TYPE_STRING},
            {'name': 'start_year', 'description': 'Find data from start year', 'type': openapi.TYPE_STRING},
            {'name': 'end_year', 'description': 'Find data up to a custom end year', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"month": "Jul", "po": 22}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def pending_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_for', 'description': "Filter for 'my' or 'team' or 'all'", 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'Team name', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"interviews": [{"id": 9543, "start_time": "2023-06-20T16:00:33Z", "marketer": "Harsh Raj"}]}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_quick_actions_data(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 4, "add_consultants": [
                {"id": 226, "name": "Greenee Anil Kumar", "email": "gs359@njit.edu"}], "search_consultant": [
                {"id": 82, "name": "Utsab Gurung", "email": "utsabgurung@gmail.com"}]}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def add_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'add_consultant', 'description': 'ID of consultant you want to add',
             'type': openapi.TYPE_INTEGER, 'required': True},
            {'name': 'search_consultant', 'description': 'ID of consultant you want to search',
             'type': openapi.TYPE_INTEGER, 'required': True},
        ],
        responses={
            200: {'description':'Success'},
            400: {'description': 'Bad Request'},
        },
        methods=['post', 'delete']
    )(view_func)

    return decorated_view
