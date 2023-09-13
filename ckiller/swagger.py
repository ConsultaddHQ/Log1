from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def list_ckiller_data(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'To filter data baed on vendor names.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'consultant',
                'description': 'ID of consultant.',
                'type': openapi.TYPE_INTEGER,
            },
            {
                'name': 'page',
                'description': 'Page number of pagination.',
                'type': openapi.TYPE_INTEGER,
            },
            {
                'name': 'page_size',
                'description': 'No of records per page.',
                'type': openapi.TYPE_INTEGER,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1376, "submission_id": 46180, "employer": "Consultadd", "project": True,
                 "sub_created": "2016-09-29T20:23:00.997000Z",
                 "job_title": "Sr, Java full stack developer/Integration Egineer at Remote", "job_location": "Remote",
                 "interview": [], "marketer": "Bhumi Vachhani", "consultant": "Nisha Karki nisha.k@consultadd.com",
                 "created": "2019-08-02T15:47:04.989000Z", "vendor": [{"name": "Geneva Consulting Group, Inc.",
                                                                       "address": "14 Vanderventer Ave., Suite 250 Port Washington, NY  11050"}],
                 "client": [{"name": "ADP", "address": None}], "rate": 63,
                 "marketing_email": "interstellar6369@gmail.com", "marketing_phone": "224-444-0883"}], "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
