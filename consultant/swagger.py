from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS
from utils_app.utils import generate_swagger_auto_schema


def list_v2_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'Name of model', 'type': openapi.TYPE_STRING},
            {'name': 'sort_by', 'description': 'To sort the list according to name or created date',
             'type': openapi.TYPE_STRING},
            {'name': 'filter_json',
             'description': 'JSON, which will filter the list by gender, city, team, recruiter, skills etcl',
             'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'Current status of the consultant', 'type': openapi.TYPE_STRING},
            {'name': 'sub_status', 'description': 'Sub status of consultant', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "count": {"total": 1, "offer": 0, "sub_status": {}, "on_bench": 1, "on_project": 1, "terminated": 0,
                          "marketing_candidate": 0}, "data": [
                    {"id": 529, "name": "Fazil Haider", "email": "fazil.h@consultadd.com", "skills": "AWS,DevOps",
                     "status": "On Project",
                     "marketing": {"rtg": False, "start": "2023-03-24", "in_pool": True, "preferred_location": "NJ",
                                   "previous_marketing_days": 0}, "recruiter": "Nupur Pandit",
                     "retention": "Abhimanyu Shekhawat", "rate": 52.5,
                     "work_auth": {"visa_end": "2023-09-30", "visa_type": "h1b", "visa_start": "2021-01-28"},
                     "exit": [], "rate_revision": False, "visa_type": "h1b"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def v2_consultant_filters(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"on_project": [], "marketing_candidate": [],
                                                                  "on_bench": [
                                                                      {"display_name": "Bench", "name": "non_pool"},
                                                                      {"display_name": "In Pool", "name": "in_pool"}],
                                                                  "offer": [
                                                                      {"display_name": "In Offer", "name": "in_offer"},
                                                                      {"display_name": "On-boarded",
                                                                       "name": "on_boarded"}], "terminated": [
                    {"display_name": "Fired", "name": "fired"}, {"display_name": "Resigned", "name": "resigned"},
                    {"display_name": "Absconded", "name": "absconded"}]}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def v2_consultant_export(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'Name of model', 'type': openapi.TYPE_STRING},
            {'name': 'filter_json',
             'description': 'JSON, which will filter the list by gender, city, team, recruiter, skills etcl',
             'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'Current status of the consultant', 'type': openapi.TYPE_STRING},
            {'name': 'sub_status', 'description': 'Sub status of consultant', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success',
                  'response': 'Name,Email,Phone Number\nFazil Haider,fazil.h@consultadd.com,+15512602176'},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def list_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'submission', 'description': 'Submission is done for consultant or not',
             'type': openapi.TYPE_BOOLEAN}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 61, "name": "Bharat Bhate", "email": "bhatebharat@gmail.com", "profiles": [
                    {"id": 76, "title": "Original", "visa_type": "gc", "visa_start": "2018-05-11",
                     "visa_end": "2028-05-11", "education": "MS in IT, Stratford University",
                     "date_of_birth": "1986-08-29", "links": None, "linkedin": None, "current_city": "New York,NY",
                     "profile_owner": {"id": 1, "employee_name": "Consultadd Admin", "email": "product@consultadd.com",
                                       "phone": "1234567890"}},
                    {"id": 201, "title": "GB-Green Card-1986-RGPV", "visa_type": "Green Card",
                     "visa_start": "2018-05-11", "visa_end": "2028-05-11", "education": "Bachelor's in CS (RGPV)",
                     "date_of_birth": "1986-08-29", "links": None, "linkedin": None, "current_city": "",
                     "profile_owner": {"id": 135, "employee_name": "Gaurav Barsale", "email": "gaurav.b@consultadd.com",
                                       "phone": "1234567890"}}]},
                {"id": 697, "name": "Bharat Bhate", "email": "bharat.b@consultadd.com", "profiles": []}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def retrieve_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'Name of consultant', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"id": 529, "name": "Fazil Haider", "email": "fazil.h@consultadd.com", "skills": "AWS,DevOps",
                         "ssn": "074538974", "gender": "male", "phone_no": "+15512602176", "links": None, "skype": None,
                         "status": "on_project", "date_of_birth": "1994-02-09", "work_type": "full_time",
                         "current_city": "Jersey City,NJ", "is_w2": False, "work_auth": [
                        {"id": 886, "is_current": True, "visa_end": "2023-09-30", "visa_start": "2021-01-28",
                         "visa_type": "h1b", "consultant": 529}],
                         "recruiter": {"id": 2733, "user_id": 49, "email": "nupur.p@consultadd.com",
                                       "phone": "19172590670", "employee_name": "Nupur Pandit"},
                         "retention": {"id": 2662, "user_id": 544, "email": "abhimanyu.s@consultadd.com",
                                       "phone": "1234567890", "employee_name": "Abhimanyu Shekhawat"},
                         "legal": {"id": 117, "user_id": 308, "email": "vikalp.s@consultadd.com",
                                   "phone": "13473452024", "employee_name": "Vikalp Singh"}, "rate": 52.5,
                         "support": {"id": 1139, "user_id": 491, "email": "mudit.t@consultadd.com",
                                     "phone": "918982780144", "employee_name": "Mudit tiwari"}, "profiles": [
                        {"id": 906, "title": "Original", "visa_type": None, "visa_start": None, "visa_end": None,
                         "education": "", "date_of_birth": None, "links": None, "linkedin": None, "current_city": None,
                         "profile_owner": {"id": 1, "employee_name": "Consultadd Admin",
                                           "email": "product@consultadd.com", "phone": "1234567890"}}], "education": [
                        {"id": 675, "title": "", "remark": "Electronics and communication", "city": "Uttar Pradesh",
                         "major": "NON-IT", "org_name": "AKTU", "edu_type": "bachelors", "start_date": None,
                         "end_date": "2016-03-15", "consultant": 529}], "terminate": [], "experience": [],
                         "marketing": {"id": 1744,
                                       "teams": [{"id": 5, "name": "Ioneq", "dept": "Marketing", "scrum_timing": None},
                                                 {"id": 6, "name": "NetResolute", "dept": "Marketing",
                                                  "scrum_timing": None},
                                                 {"id": 1, "name": "Consultadd", "dept": "Management",
                                                  "scrum_timing": None}],
                                       "marketer": [{"id": 280, "name": "Akshay Mishra"},
                                                    {"id": 920, "name": "Anshika Khandelwal"}], "status": "open",
                                       "in_pool": True, "rtg": False, "start": "2023-03-24", "end": None,
                                       "preferred_location": "NJ",
                                       "primary_marketer": {"id": 280, "employee_name": "Akshay Mishra",
                                                            "email": "akshay.m@consultadd.com",
                                                            "phone": "917987491917"}, "previous_marketing_days": 0},
                         "payroll_employer": {"id": 960, "name": "Consultadd", "start": "2023-01-02",
                                              "created": "2023-01-04T19:09:05.035777Z"}, "internal_employee": False,
                         "marital_status": None,
                         "active_marketer": {"id": 1744, "user_id": 280, "email": "akshay.m@consultadd.com",
                                             "phone": "917987491917", "employee_name": "Akshay Mishra"},
                         "timezone": "EDT", "country": "USA"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def consultant_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of consultant'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email id of consultant'),
                'ssn': openapi.Schema(type=openapi.TYPE_STRING, description='SSN number of consultant'),
                'skills': openapi.Schema(type=openapi.TYPE_STRING, description='Technical skills of consultant'),
                'skype': openapi.Schema(type=openapi.TYPE_STRING, description='Skype ID of consultant'),
                'phone_no': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of consultant'),
                'current_city': openapi.Schema(type=openapi.TYPE_STRING, description='Current city of consultant'),
                'recruiter': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the recruiter'),
                'retention': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of retention'),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of consultant'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of consultant'),
                'links': openapi.Schema(type=openapi.TYPE_STRING, description='Links of consultant'),
                'work_type': openapi.Schema(type=openapi.TYPE_STRING,
                                            description='Work type of consultant (full_time, part_time etc.)'),
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Visa Type of consultant'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa'),
                'payroll_employer': openapi.Schema(type=openapi.TYPE_STRING, description='Name of payroll employer'),
                'employer_start_date': openapi.Schema(type=openapi.TYPE_STRING, description='Payroll start date'),
                'is_w2': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Project type is w2 or not'),
                'marital_status': openapi.Schema(type=openapi.TYPE_STRING, description='Marital status of consultant'),
                'internal_employee': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description='Consultant is internal employee or not'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of consultant')
            },
            [
                'name', 'email', 'ssn', 'skills', 'phone_no', 'current_city', 'recruiter', 'date_of_birth', 'gender',
                'visa_type', 'visa_start', 'visa_end', 'payroll_employer', 'employer_start_date', 'is_w2', 'country'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 1128, "last_login": None, "created": "2023-08-14T09:43:53.622446Z",
                         "modified": "2023-08-14T09:43:54.488064Z", "is_w2": True, "is_active": False,
                         "first_login": True, "remote_only": False, "email": "sdfgh@test.com",
                         "internal_employee": False, "name": "Naksh Sharma", "ssn": "959595959",
                         "date_of_birth": "2023-06-06", "links": None, "domain": None,
                         "skills": "SQL,ReactJS,JavaScript", "skype": None, "country": "USA", "timezone": "EDT",
                         "phone_no": "14567890098", "current_city": "Abbot,ME", "marital_status": None,
                         "gender": "male", "status": "on_bench", "work_type": "full_time", "p_is_active": False,
                         "visa_petition": False, "pin": None}}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of consultant'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email id of consultant'),
                'ssn': openapi.Schema(type=openapi.TYPE_STRING, description='SSN number of consultant'),
                'skills': openapi.Schema(type=openapi.TYPE_STRING, description='Technical skills of consultant'),
                'skype': openapi.Schema(type=openapi.TYPE_STRING, description='Skype ID of consultant'),
                'phone_no': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of consultant'),
                'current_city': openapi.Schema(type=openapi.TYPE_STRING, description='Current city of consultant'),
                'recruiter': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the recruiter'),
                'retention': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of retention'),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of consultant'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of consultant'),
                'links': openapi.Schema(type=openapi.TYPE_STRING, description='Links of consultant'),
                'work_type': openapi.Schema(type=openapi.TYPE_STRING,
                                            description='Work type of consultant (full_time, part_time etc.)'),
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Visa Type of consultant'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa'),
                'payroll_employer': openapi.Schema(type=openapi.TYPE_STRING, description='Name of payroll employer'),
                'employer_start_date': openapi.Schema(type=openapi.TYPE_STRING, description='Payroll start date'),
                'is_w2': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Project type is w2 or not'),
                'marital_status': openapi.Schema(type=openapi.TYPE_STRING, description='Marital status of consultant'),
                'internal_employee': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description='Consultant is internal employee or not'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of consultant')
            },
            [
                'name', 'email', 'ssn', 'skills', 'phone_no', 'current_city', 'recruiter', 'date_of_birth', 'gender',
                'visa_type', 'visa_start', 'visa_end', 'payroll_employer', 'employer_start_date', 'is_w2', 'country'
            ],
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1128, "last_login": None, "created": "2023-08-14T09:43:53.622446Z",
                         "modified": "2023-08-14T09:43:54.488064Z", "is_w2": True, "is_active": False,
                         "first_login": True, "remote_only": False, "email": "sdfgh@test.com",
                         "internal_employee": False, "name": "Naksh Sharma", "ssn": "959595959",
                         "date_of_birth": "2023-06-06", "links": None, "domain": None,
                         "skills": "SQL,ReactJS,JavaScript", "skype": None, "country": "USA", "timezone": "EDT",
                         "phone_no": "14567890098", "current_city": "Abbot,ME", "marital_status": None,
                         "gender": "male", "status": "on_bench", "work_type": "full_time", "p_is_active": False,
                         "visa_petition": False, "pin": None}}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def update_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of consultant.'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email id of consultant.'),
                'ssn': openapi.Schema(type=openapi.TYPE_STRING, description='SSN number of consultant.'),
                'skills': openapi.Schema(type=openapi.TYPE_STRING, description='Technical skills of consultant.'),
                'skype': openapi.Schema(type=openapi.TYPE_STRING, description='Skype ID of consultant.'),
                'phone_no': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of consultant.'),
                'current_city': openapi.Schema(type=openapi.TYPE_STRING, description='Current city of consultant.'),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of consultant.'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of consultant.'),
                'is_w2': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Project type is w2 or not.'),
                'marital_status': openapi.Schema(type=openapi.TYPE_STRING, description='Marital status of consultant.'),
                'internal_employee': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description='Consultant is internal employee or not.'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of consultant.')
            },
            [
            ],
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1128, "last_login": None, "is_w2": True, "is_active": False, "first_login": True,
                         "remote_only": False, "email": "sdfgh@test.com", "internal_employee": False,
                         "name": "Naksh Sharma", "ssn": "959595959", "date_of_birth": "2023-06-06", "links": None,
                         "domain": None, "skills": "SQL,ReactJS,JavaScript", "skype": None, "country": "USA",
                         "timezone": "EDT", "phone_no": "14567890098", "current_city": "Abbot,ME",
                         "marital_status": None, "gender": "male", "status": "on_bench", "work_type": "full_time",
                         "p_is_active": False, "visa_petition": False, "pin": None}, "message": "Consultant Updated"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_activities(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 80000, "user": {"id": 998, "employee_id": 2344,
                                                                                         "email": "v.s@c.com",
                                                                                         "employee_name": "v s",
                                                                                         "team": "Consultadd",
                                                                                         "roles": ["engineer"],
                                                                                         "gender": "male",
                                                                                         "phone": "9393939393",
                                                                                         "avatar": None,
                                                                                         "is_superuser": False,
                                                                                         "technology": None},
                                                                   "activity_type": "created",
                                                                   "desc": "s s added consultant manually",
                                                                   "object_id": 1128,
                                                                   "created": "2023-08-14T09:43:54.499485Z",
                                                                   "content_type": 20}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_set_password(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'consultant_id', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER,
             'required': True},
            {'name': 'new_password', 'description': 'New password of consultant', 'type': openapi.TYPE_STRING,
             'required': True},
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Password Changed Successfully"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_search(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'Name of consultant', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 138, "name": "Sameer Kulkarni", "email": "reachsameerk@gmail.com"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_education_post(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City of organization.'),
                'major': openapi.Schema(type=openapi.TYPE_STRING, description='Field of education.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Any remarks for education.'),
                'org_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of organization.'),
                'edu_type': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Type of education (bachelors, masters, etc.).'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, description='Graduation date of consultant.')
            },
            ['city', 'major', 'remark', 'org_name', 'edu_type', 'end_date']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 1033, "title": "", "remark": "Good", "city": "Indore", "major": "IT", "org_name": "AITR",
                         "edu_type": "bachelors", "start_date": None, "end_date": "2023-03-09", "consultant": "1128"},
                "message": "Education details added"}},
            400: {'description': 'Bad Request'}
        },
        methods=['post']
    )(view_func)
    return decorated_view


def consultant_education_put(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City of organization.'),
                'major': openapi.Schema(type=openapi.TYPE_STRING, description='Field of education.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Any remarks for education.'),
                'org_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of organization.'),
                'edu_type': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Type of education (bachelors, masters, etc.).'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, description='Graduation date of consultant.')
            },
            ['city', 'major', 'remark', 'org_name', 'edu_type', 'end_date']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1033, "title": "", "remark": "Good", "city": "Indore", "major": "IT", "org_name": "AITR",
                         "edu_type": "bachelors", "start_date": None, "end_date": "2023-03-09", "consultant": 1128},
                "message": "Education details updated"}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)
    return decorated_view


def consultant_experience_post(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City of company.'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title of experience.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Any remarks for experience.'),
                'company': openapi.Schema(type=openapi.TYPE_STRING, description='Name of company.'),
                'exp_type': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Type of experience (part time, full time etc).'),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of experience.'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, description='End date of experience.')
            },
            ['city', 'title', 'remark', 'company', 'exp_type', 'start_date', 'end_date']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 606, "title": "SDE", "remark": "Good", "city": "Indore", "company": "Amazon",
                         "exp_type": "Full Time", "start_date": "2021-03-12", "end_date": "2022-03-13",
                         "consultant": "1128"}, "message": "Experience details added"}},
            400: {'description': 'Bad Request'}
        },
        methods=['post']
    )(view_func)
    return decorated_view


def consultant_experience_put(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City of company.'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title of experience.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Any remarks for experience.'),
                'company': openapi.Schema(type=openapi.TYPE_STRING, description='Name of company.'),
                'exp_type': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Type of experience (part time, full time etc).'),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of experience.'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, description='End date of experience.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 606, "title": "SDE", "remark": "Good", "city": "Indore", "company": "Amazon",
                         "exp_type": "Full Time", "start_date": "2021-03-12", "end_date": "2022-03-13",
                         "consultant": 1128}, "message": "Experience details updated"}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)
    return decorated_view


def consultant_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_by_status', 'description': 'Filter data based on status', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 977, "city": "Remote,US", "rate": 80.0, "created": "2021-12-29T17:00:39.638931Z",
                 "employer": "Consultadd", "start_date": "2022-01-24", "end_date": "2022-08-13", "is_remote": False,
                 "client": "Capital One", "work_type": "c2c", "consultant_name": "Khatija Jamani",
                 "job_title": "Python Developer", "status": "joined", "company_name": "Pinnacle Group Inc",
                 "marketer_name": "Akriti Mishra"}], "total": {"total": 5, "new": 0, "joined": 1, "received": 0,
                                                               "on_boarded": 0, "not_joined": 0}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def consultant_documents(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 130632, "object_id": 1121, "attachment_type": "other", "file_name": "Chintan_Resume.pdf",
                 "type": {"name": "other", "display_name": "Other"}}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def consultant_payroll_employer_get(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 998, "name": "Consultadd", "start": "2023-06-13", "created": "2023-08-14T09:43:54.496474Z"}]}},
            400: {'description': 'Bad Request'},
        },
        methods=['get']
    )(view_func)
    return decorated_view


def consultant_payroll_employer_post(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of payroll employer.'),
                'start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of payroll.')
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": [
                {"id": 998, "name": "Consultadd", "start": "2023-06-13", "created": "2023-08-14T09:43:54.496474Z"}]}},
            400: {'description': 'Bad Request'},
        },
        methods=['post']
    )(view_func)
    return decorated_view


def consultant_payroll_employer_put(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of payroll employer.'),
                'start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of payroll.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": {"id": 999, "name": "Microsoft", "start": "2021-12-03",
                                                                  "created": "2023-08-14T10:18:29.450803Z"},
                                                         "message": "Employer updated"}},
            400: {'description': 'Bad Request'},
        },
        methods=['put']
    )(view_func)
    return decorated_view


def consultant_rate_revision_get(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1209, "rate": 60.0, "start": "2022-01-03", "end": None, "previous_rate": 56.0, "feedback": "",
                 "consultant": 40},
                {"id": 1014, "rate": 56.0, "start": "2021-07-23", "end": "2021-12-28", "previous_rate": 112.0,
                 "feedback": "Her waste management project got terminated.", "consultant": 40},
                {"id": 991, "rate": 112.0, "start": "2021-07-15", "end": "2021-07-27", "previous_rate": 56.0,
                 "feedback": "$56 - Waste Management\n$56 - Capital one ", "consultant": 40},
                {"id": 831, "rate": 56.0, "start": "2021-02-09", "end": "2021-07-15", "previous_rate": 50.0,
                 "feedback": "", "consultant": 40},
                {"id": 387, "rate": 50.0, "start": "2020-04-06", "end": "2021-02-09", "previous_rate": 55.0,
                 "feedback": "", "consultant": 40},
                {"id": 14, "rate": 55.0, "start": "2020-03-04", "end": "2020-04-07", "previous_rate": 0.0,
                 "feedback": None, "consultant": 40}]}},
            400: {'description': 'Bad Request'},
        },
        methods=['get']
    )(view_func)
    return decorated_view


def consultant_rate_revision_post(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.'),
                'rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='Rate of consultant.'),
                'start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of rate revision.'),
                'feedback': openapi.Schema(type=openapi.TYPE_STRING, description='Feedback (if any).'),
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.')
            },
            ['id', 'rate', 'start', 'feedback', 'consultant']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": {"id": 1829, "created": "2023-08-14T10:25:22.231740Z",
                                                                  "modified": "2023-08-14T10:25:22.231748Z",
                                                                  "rate": 55.0, "previous_rate": 0.0,
                                                                  "start": "2020-03-04", "feedback": "feedback",
                                                                  "end": None, "consultant": 1128},
                                                         "message": "Rate revised"}},
            400: {'description': 'Bad Request'},
        },
        methods=['post']
    )(view_func)
    return decorated_view


def consultant_margin(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"margin": 20.0, "projects": [
                {"id": 977, "rate": 80.0, "status": "Joined", "client": "Capital One"},
                {"id": 684, "rate": 82.0, "status": "Project Completed", "client": "Waste Management"},
                {"id": 676, "rate": 97.5, "status": "Project Completed", "client": "Capital one"},
                {"id": 482, "rate": 75.0, "status": "Project Terminated", "client": "Austin Community College"},
                {"id": 10, "rate": 90.0, "status": "Project Terminated", "client": "At Home"}],
                                                                  "margin_percentage": 25.0, "lock_flag": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def list_consultant_bench(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'status', 'description': 'Filter data based on status', 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'Filter data based on team', 'type': openapi.TYPE_STRING},
            {'name': 'gender', 'description': 'Filter data based on gender', 'type': openapi.TYPE_STRING},
            {'name': 'skills', 'description': 'Filter data based on skills', 'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'Filter data based on query', 'type': openapi.TYPE_STRING},
            {'name': 'days', 'description': 'Filter data based on days', 'type': openapi.TYPE_INTEGER},
            {'name': 'visa', 'description': 'Filter data based on visa type', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 201, "name": "Ankur Pathania", "skills": "BA,Python", "rate": 65.0, "rtg": False, "visa": "gc",
                 "in_pool": False, "marketing_start": "2023-05-15", "recruiter": "Nidhi Tiwari Tiwari",
                 "preferred_location": "California", "previous_marketing_days": 0}],
                "count": {"total": 1, "in_pool": 0, "in_offer": 0,
                          "on_project": 1, "on_boarded": 0, "in_marketing": 1,
                          "candidate": 0}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def list_consultant_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'consultant', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 1802, "cycle": 1, "teams": [
                {"id": 41, "name": "Consultadd Canada", "dept": "Marketing", "scrum_timing": None}], "status": "close",
                                                                   "in_pool": False, "rtg": True, "start": "2023-05-17",
                                                                   "end": "2023-05-17",
                                                                   "preferred_location": "Waterloo,ON",
                                                                   "project_count": 0,
                                                                   "primary_marketer": "Arpit Mehta",
                                                                   "primary_marketer_team": "Consultadd Canada",
                                                                   "submission_count": 0, "interview_count": 0,
                                                                   "current_city": "Waterloo Canada"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def create_consultant_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.'),
                'marketing_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of marketing.'),
                'preferred_location': openapi.Schema(type=openapi.TYPE_STRING,
                                                     description='Preferred location of consultant.'),
                'primary_marketer': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of primary marketer.'),
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY,
                                        description='List of teams who are doing consultant\'s marketing.',
                                        items=openapi.Items(type=openapi.TYPE_STRING)),
                'marketers': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of IDS of secondary marketer.',
                                            items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'rtg': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is consultant ready to go.'),
                'in_pool': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is consultant in pool.'),
                'reset_days': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                             description='Do you want to reset the counter of marketing cycle.')
            },
            ['consultant', 'in_pool']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Marketing started"}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not Found', 'response': {"message": "Consultant not found"}}
        }
    )(view_func)
    return decorated_view


def update_consultant_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'marketing_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of marketing.'),
                'preferred_location': openapi.Schema(type=openapi.TYPE_STRING,
                                                     description='Preferred location of consultant.'),
                'primary_marketer': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of primary marketer.'),
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY,
                                        description='List of teams who are doing consultant\'s marketing.',
                                        items=openapi.Items(type=openapi.TYPE_STRING)),
                'marketers': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of IDS of secondary marketer.',
                                            items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'rtg': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is consultant ready to go.'),
                'in_pool': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is consultant in pool.'),
                'reset_days': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                             description='Do you want to reset the counter of marketing cycle.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Marketing cycle updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_marketing_stop_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of marketing.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Marketing cycle stopped"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_marketing_remarketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'consultant', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 1802, "cycle": 1, "teams": [
                {"id": 41, "name": "Consultadd Canada", "dept": "Marketing", "scrum_timing": None}], "status": "close",
                                                                   "in_pool": False, "rtg": True, "start": "2023-05-17",
                                                                   "end": "2023-05-17",
                                                                   "preferred_location": "Waterloo,ON",
                                                                   "project_count": 0,
                                                                   "primary_marketer": "Arpit Mehta",
                                                                   "primary_marketer_team": "Consultadd Canada",
                                                                   "submission_count": 0, "interview_count": 0,
                                                                   "current_city": "Waterloo Canada"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def consultant_marketing_previous_marketing(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'consultant', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 1802, "cycle": 1, "teams": [
                {"id": 41, "name": "Consultadd Canada", "dept": "Marketing", "scrum_timing": None}], "status": "close",
                                                                  "in_pool": False, "rtg": True, "start": "2023-05-17",
                                                                  "end": "2023-05-17",
                                                                  "preferred_location": "Waterloo,ON",
                                                                  "project_count": 0, "primary_marketer": "Arpit Mehta",
                                                                  "primary_marketer_team": "Consultadd Canada",
                                                                  "submission_count": 0, "interview_count": 0,
                                                                  "current_city": "Waterloo Canada"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def consultant_marketing_marketer_assignment(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'marketers': openapi.Schema(type=openapi.TYPE_ARRAY, description='ID of marketers',
                                            items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['marketers']
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": [
                {"id": 351, "employee_name": "Zahid hasan", "email": "zahid.h@consultadd.com", "phone": "9119213812"}],
                "message": "marketers assigned"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_marketing_team_assignment(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY, description='IDS of teams',
                                        items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['teams']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": [{"id": 3, "name": "Elegant Team", "dept": "Marketing", "scrum_timing": "12:00 PM - 12:30 PM"}],
                "message": "Team added"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_marketing_remove_marketer(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'marketers': openapi.Schema(type=openapi.TYPE_ARRAY, description='IDS of marketers',
                                            items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['marketers']
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": [
                {"id": 351, "employee_name": "Zahid hasan", "email": "zahid.h@consultadd.com", "phone": "9119213812"}],
                "message": "Marketers removed"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_marketing_remove_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY, description='IDS of teams',
                                        items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['teams']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": [{"id": 8, "name": "OC10", "dept": "Marketing", "scrum_timing": None}],
                               "message": "Team removed"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def retrieve_consultant_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"id": 1137, "title": "Original", "visa_type": None, "visa_start": None, "visa_end": None,
                         "education": None, "date_of_birth": "1997-08-31",
                         "links": "['https://www.linkedin.com/in/chintan-limbani-a22635103/']", "linkedin": None,
                         "current_city": "Waterloo Canada",
                         "profile_owner": {"id": 1, "employee_name": "Consultadd Admin",
                                           "email": "product@consultadd.com", "phone": "1234567890"}}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def list_consultant_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'con_id', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1137, "title": "Original", "visa_type": None, "visa_start": None, "visa_end": None,
                 "education": None, "date_of_birth": "1997-08-31",
                 "links": "['https://www.linkedin.com/in/chintan-limbani-a22635103/']", "linkedin": None,
                 "current_city": "Waterloo Canada",
                 "profile_owner": {"id": 1, "employee_name": "Consultadd Admin", "email": "product@consultadd.com",
                                   "phone": "1234567890"}}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def create_consultant_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title of profile.'),
                'links': openapi.Schema(
                    type=openapi.TYPE_STRING, description='Links of consultant.'),
                'linkedin': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Linkedin profile link of consultant.'),
                'dob': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of consultant.'),
                'current_city': openapi.Schema(type=openapi.TYPE_STRING, description='Current city of consultant.'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa.'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa.'),
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of visa consultant is having.'),
                'education': openapi.Schema(type=openapi.TYPE_STRING, description='Education details of consultant.'),
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.')
            },
            [
                'title', 'links', 'linkedin', 'dob', 'current_city', 'visa_end', 'visa_start', 'visa_type', 'education',
                'consultant'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 1147, "title": "VS-gc-2000-Green Card Profile", "visa_type": "gc",
                         "visa_start": "2023-06-14", "visa_end": "2029-06-01", "education": "MS",
                         "date_of_birth": "2000-01-01", "links": "code.com", "linkedin": "linkedin.com/naksh",
                         "current_city": "Abbeville,LA",
                         "profile_owner": {"id": 998, "employee_name": "v s", "email": "v.s@c.com",
                                           "phone": "917723870656"}}, "message": "Profile created"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def update_consultant_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title of profile.'),
                'links': openapi.Schema(
                    type=openapi.TYPE_STRING, description='Links of consultant.'),
                'linkedin': openapi.Schema(type=openapi.TYPE_STRING,
                                           description='Linkedin profile link of consultant.'),
                'dob': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of consultant.'),
                'current_city': openapi.Schema(type=openapi.TYPE_STRING, description='Current city of consultant.'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa.'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa.'),
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of visa consultant is having.'),
                'education': openapi.Schema(type=openapi.TYPE_STRING, description='Education details of consultant.')
            },
            [
                'title', 'links', 'linkedin', 'dob', 'current_city', 'visa_end', 'visa_start', 'visa_type', 'education',
                'consultant'
            ],
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1121, "title": "Green Card Profile", "visa_type": "gc", "visa_start": "2023-06-14",
                         "visa_end": "2029-06-01", "education": "MTECH", "date_of_birth": None, "links": "coder.com",
                         "linkedin": "linkedin.com/naksh", "current_city": "Abbeville,LA",
                         "profile_owner": {"id": 1, "employee_name": "Consultadd Admin",
                                           "email": "product@consultadd.com", "phone": "1234567890"}},
                "message": "Profile updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def create_consultant_poc(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.'),
                'poc': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of POC.'),
                'poc_type': openapi.Schema(type=openapi.TYPE_STRING, description='Department of POC.')
            },
            [
                'consultant', 'poc', 'poc_type'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "POC added"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def update_consultant_poc(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'poc': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of POC.'),
                'poc_type': openapi.Schema(type=openapi.TYPE_STRING, description='Department of POC.')
            },
            [],
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1128, "start": "2021-01-27", "end": None, "poc_type": "marketer", "poc": 914,
                         "consultant": 578}, "message": "POC updated"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def create_consultant_work_auth(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.'),
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of visa consultant is having.'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa.'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa.')
            },
            [
                'consultant', 'visa_type', 'visa_start'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 1223, "is_current": True, "visa_end": "2025-04-23", "visa_start": "2023-03-20",
                         "visa_type": "l2_ead", "consultant": 1128}, "message": "Work Auth added"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def update_consultant_work_auth(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'visa_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of visa consultant is having.'),
                'visa_start': openapi.Schema(type=openapi.TYPE_STRING, description='Start date of visa.'),
                'visa_end': openapi.Schema(type=openapi.TYPE_STRING, description='End date of visa.')
            },
            [],
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 1223, "is_current": True, "visa_end": "2025-04-23", "visa_start": "2023-03-20",
                         "visa_type": "l2_ead", "consultant": 1128}, "message": "Work Auth added"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def list_consultant_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'con_id', 'description': 'ID of consultant', 'type': openapi.TYPE_INTEGER, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1137, "title": "Original", "visa_type": None, "visa_start": None, "visa_end": None,
                 "education": None, "date_of_birth": "1997-08-31",
                 "links": "['https://www.linkedin.com/in/chintan-limbani-a22635103/']", "linkedin": None,
                 "current_city": "Waterloo Canada",
                 "profile_owner": {"id": 1, "employee_name": "Consultadd Admin", "email": "product@consultadd.com",
                                   "phone": "1234567890"}}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def list_consultant_exit(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data based on query', 'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'To filter data based on status', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 244, "name": "Mayank Gandhi", "skills": "BA", "type": "fired", "rehire": False,
                 "last_date": "2020-02-10"}], "count": {"total": 7, "fired": 2, "resigned": 5, "absconded": 0}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def create_consultant_exit(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'consultant': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of consultant.'),
                'type': openapi.Schema(type=openapi.TYPE_STRING, description='Termination type of consultant.'),
                'resign_date': openapi.Schema(type=openapi.TYPE_STRING,
                                              description='Date of resignation of consultant.'),
                'last_date': openapi.Schema(type=openapi.TYPE_STRING, description='Date of relieving of consultant.'),
                'rehire': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Consultant is fit to rehire.'),
                'exit_details': openapi.Schema(type=openapi.TYPE_STRING, description='Details of resignation.'),
                'notice_period': openapi.Schema(type=openapi.TYPE_INTEGER, description='No of days of notice period.'),
                'reasons': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of reasons of exit.',
                                          items=openapi.Items(type=openapi.TYPE_STRING)),
                'legal_action': openapi.Schema(type=openapi.TYPE_STRING,
                                               description='Any legal action taken on consultant.'),
                'legal_status': openapi.Schema(type=openapi.TYPE_STRING, description='Status of legal action.')
            },
            ['consultant', 'type']
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": [
                {"id": 670, "created": "2023-08-14T12:13:20.585272Z", "type": "resigned", "status": "complete",
                 "rehire": True, "created_by": 998, "last_date": "2023-06-14", "resign_date": "2023-06-14",
                 "exit_details": "<p>Details of exit.</p>",
                 "reasons": [{"id": 2, "name": "Visa Expiration"}, {"id": 1, "name": "New Job Offer from Other"}],
                 "notice_period": 30, "legal_action": True, "legal_status": "solved", "tagged_user": [],
                 "cancel_reason": None},
                {"id": 669, "created": "2023-08-14T12:13:10.601132Z", "type": "resigned", "status": "in_process",
                 "rehire": False, "created_by": 998, "last_date": None, "resign_date": None, "exit_details": None,
                 "reasons": [], "notice_period": None, "legal_action": False, "legal_status": None, "tagged_user": [],
                 "cancel_reason": None},
                {"id": 667, "created": "2023-08-14T12:12:40.169593Z", "type": "resigned", "status": "complete",
                 "rehire": True, "created_by": 998, "last_date": "2023-06-14", "resign_date": "2023-06-14",
                 "exit_details": "<p>Details of exit.</p>",
                 "reasons": [{"id": 2, "name": "Visa Expiration"}, {"id": 1, "name": "New Job Offer from Other"}],
                 "notice_period": 30, "legal_action": True, "legal_status": "solved", "tagged_user": [],
                 "cancel_reason": None}], "exit_mail": "Development Server", "message": "Exit process created"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def update_consultant_exit(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'type': openapi.Schema(type=openapi.TYPE_STRING, description='Termination type of consultant.'),
                'resign_date': openapi.Schema(type=openapi.TYPE_STRING,
                                              description='Date of resignation of consultant.'),
                'last_date': openapi.Schema(type=openapi.TYPE_STRING, description='Date of relieving of consultant.'),
                'rehire': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Consultant is fit to rehire.'),
                'exit_details': openapi.Schema(type=openapi.TYPE_STRING, description='Details of resignation.'),
                'notice_period': openapi.Schema(type=openapi.TYPE_INTEGER, description='No of days of notice period.'),
                'reasons': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of reasons of exit.',
                                          items=openapi.Items(type=openapi.TYPE_STRING)),
                'legal_action': openapi.Schema(type=openapi.TYPE_STRING,
                                               description='Any legal action taken on consultant.'),
                'legal_status': openapi.Schema(type=openapi.TYPE_STRING, description='Status of legal action.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 662, "created": "2023-07-31T08:29:43.068450Z", "type": "resigned", "status": "complete",
                         "rehire": False, "created_by": 1, "last_date": "2023-06-17", "resign_date": "2023-06-14",
                         "exit_details": "<p>Details of exit.</p>",
                         "reasons": [{"id": 2, "name": "Visa Expiration"}, {"id": 4, "name": "Health Issues"},
                                     {"id": 5, "name": "Technology Issues"},
                                     {"id": 1, "name": "New Job Offer from Other"}], "notice_period": 20,
                         "legal_action": False, "legal_status": None, "tagged_user": [], "cancel_reason": None},
                "message": "Exit process updated"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_exit_cancel(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'cancel_reason': openapi.Schema(type=openapi.TYPE_STRING, description='Reason of cancellation'),
            },
            ['cancel_reason']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 662, "created": "2023-07-31T08:29:43.068450Z", "type": "resigned", "status": "cancelled",
                         "rehire": False, "created_by": 1, "last_date": "2023-06-17", "resign_date": "2023-06-14",
                         "exit_details": "<p>Details of exit.</p>",
                         "reasons": [{"id": 2, "name": "Visa Expiration"}, {"id": 4, "name": "Health Issues"},
                                     {"id": 5, "name": "Technology Issues"},
                                     {"id": 1, "name": "New Job Offer from Other"}], "notice_period": 20,
                         "legal_action": False, "legal_status": None, "tagged_user": [],
                         "cancel_reason": "Consultant want to join again"}, "exit_mail": "Development Server",
                "message": "Exit process cancelled"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_exit_reason(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"id": 2, "name": "Visa Expiration"}, {"id": 3, "name": "Career Change"},
                         {"id": 4, "name": "Health Issues"}, {"id": 5, "name": "Technology Issues"},
                         {"id": 6, "name": "Maritial Issues"}, {"id": 7, "name": "Higher Studies"},
                         {"id": 8, "name": "Full Time Opportuinty"}, {"id": 9, "name": "Location Change"},
                         {"id": 10, "name": "Personal Issues"}, {"id": 11, "name": "Work Environment Problems"},
                         {"id": 12, "name": "Performance Issues"}, {"id": 13, "name": "Support Issue"},
                         {"id": 14, "name": "Join Direct to Client"}, {"id": 15, "name": "Others"},
                         {"id": 16, "name": "New Job Offer from Client"},
                         {"id": 17, "name": "New Job Offer from Vendor"},
                         {"id": 1, "name": "New Job Offer from Other"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def beats_consultant_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API key of log1.'),
                'links': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of links of candidate.',
                                        items=openapi.Items(type=openapi.TYPE_STRING)),
                'skills': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of skills of candidate.',
                                         items=openapi.Items(type=openapi.TYPE_STRING)),
                'phone_numbers': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                description='List of phone numbers of candidate.',
                                                items=openapi.Items(type=openapi.TYPE_STRING)),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email id of candidate.'),
                'ssn': openapi.Schema(type=openapi.TYPE_STRING, description='SSN number of candidate.'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of candidate.'),
                'skype_id': openapi.Schema(type=openapi.TYPE_STRING, description='Skype id of candidate.'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of candidate.'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of candidate.'),
                'dob': openapi.Schema(type=openapi.TYPE_STRING, description='Date of birth of candidate.'),
                'current_location': openapi.Schema(type=openapi.TYPE_STRING,
                                                   description='Current location of candidate.'),
                'marital_status': openapi.Schema(type=openapi.TYPE_STRING, description='Marital status of candidate.'),
                'internal_employee': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description='Is candidate internal employee.'),
                'recruiter': openapi.Schema(type=openapi.TYPE_STRING, description='Email ID of recruiter.'),
                'rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='Rate of candidate.'),
                'work_auth': openapi.Schema(type=openapi.TYPE_ARRAY, description='Work auth details of candidate.',
                                            items=openapi.Items(type=openapi.TYPE_OBJECT)),
                'education': openapi.Schema(type=openapi.TYPE_ARRAY, description='Education details of candidate.',
                                            items=openapi.Items(type=openapi.TYPE_OBJECT)),
                'experience': openapi.Schema(type=openapi.TYPE_ARRAY, description='Experience detail of candidate.',
                                             items=openapi.Items(type=openapi.TYPE_OBJECT)),
                'documents': openapi.Schema(type=openapi.TYPE_ARRAY, description='Documents of candidate.',
                                            items=openapi.Items(type=openapi.TYPE_OBJECT))
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Consultant Created on Log1"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def list_consultant_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data based on query', 'type': openapi.TYPE_STRING},
            {'name': 'feedback_type', 'description': 'To filter data based on feedback type',
             'type': openapi.TYPE_STRING},
            {'name': 'project', 'description': 'ID of project', 'type': openapi.TYPE_INTEGER},
        ],
        responses={
            200: {'description': 'Success', 'response': {"count": 3, "data": [
                {"id": 478, "project": {"id": 1081, "client_name": "Expedia", "vendor_name": "Bluehawk Consulting"},
                 "created_by": "Gyanendra Singh Chandrawat", "consultant": "Nishant Tomar", "tagged_user": [],
                 "feedback_type": "Engineering Issue", "department": "engineering",
                 "created": "2022-07-19T15:50:53.451321Z", "modified": "2022-07-22T06:38:33.712702Z",
                 "description": "description", "rating": 1, "verdict": None}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def create_consultant_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of feedback.'),
                'project': openapi.Schema(type=openapi.TYPE_INTEGER,
                                          description='ID of project for which feedback is submitted.'),
                'rating': openapi.Schema(type=openapi.TYPE_INTEGER, description='Rating of feedback.'),
                'department': openapi.Schema(type=openapi.TYPE_STRING, description='Department of feedback.'),
                'feedback_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                description='Type of feedback you are submitting.'),
                'verdict': openapi.Schema(type=openapi.TYPE_STRING, description='Verdict of feedback.'),
                'tagged_user': openapi.Schema(type=openapi.TYPE_ARRAY,
                                              description='Any employee you want to tag for feedback.',
                                              items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['description', 'feedback_type']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": {"id": 826,
                                                                  "project": {"id": 1081, "client_name": "Expedia",
                                                                              "vendor_name": "Bluehawk Consulting"},
                                                                  "created_by": "Raj", "consultant": "Nishant Tomar",
                                                                  "tagged_user": [],
                                                                  "feedback_type": "Engineering Issue",
                                                                  "department": "engineering",
                                                                  "created": "2023-08-14T13:06:45.545855Z",
                                                                  "modified": "2023-08-14T13:06:45.548054Z",
                                                                  "description": "Description of feedback", "rating": 4,
                                                                  "verdict": "Good"}, "message": "Feedback added"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def update_consultant_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of feedback.'),
                'project': openapi.Schema(type=openapi.TYPE_INTEGER,
                                          description='ID of project for which feedback is submitted.'),
                'rating': openapi.Schema(type=openapi.TYPE_INTEGER, description='Rating of feedback.'),
                'department': openapi.Schema(type=openapi.TYPE_STRING, description='Department of feedback.'),
                'feedback_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                description='Type of feedback you are submitting.'),
                'verdict': openapi.Schema(type=openapi.TYPE_STRING, description='Verdict of feedback.'),
                'tagged_user': openapi.Schema(type=openapi.TYPE_ARRAY,
                                              description='Any employee you want to tag for feedback.',
                                              items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": {"data": {"id": 822, "project": {"id": 1336,
                                                                                                  "client_name": "T. Rowe Price",
                                                                                                  "vendor_name": "Vision Technology"},
                                                                           "created_by": "Darshan hirekurubar",
                                                                           "consultant": "Samyak Jain",
                                                                           "tagged_user": [],
                                                                           "feedback_type": "Engineering Issue",
                                                                           "department": "engineering",
                                                                           "created": "2023-08-11T08:08:43.476749Z",
                                                                           "modified": "2023-08-14T13:11:14.666893Z",
                                                                           "description": "Description of feedback",
                                                                           "rating": 2, "verdict": "Good"},
                                                                  "message": "Feedback updated"}}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)
    return decorated_view


def consultant_feedback_types(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": [["cfr", "CFR"], ["green_card", "Green Card"], ["independent", "Independent"],
                         ["pre_joining", "Pre Joining"], ["2_week", "2 Week of Joining"],
                         ["re_marketing", "Re-marketing"], ["rate_increment", "Rate Increment"],
                         ["engineering_issue", "Engineering Issue"]]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_feedback_department(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": ["Engineering", "Marketing", "Legal", "Recruitment", "Relations", "Finance"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_feedback_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"id": 1081, "vendor": "Bluehawk Consulting", "client": "Expedia"},
                         {"id": 675, "vendor": "Granite Solutions Groupe", "client": "First Republic Bank"},
                         {"id": 459, "vendor": "Enterprise Engineering Inc.", "client": "Morgan Stanley"},
                         {"id": 54, "vendor": "Combined Computer Resources Inc", "client": "Hudson Bay Company"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_feedback_request(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'department': openapi.Schema(type=openapi.TYPE_ARRAY, description='ID of departments',
                                             items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'feedback_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of feedback'),
            },
            ['feedback_type']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "mail sent"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def consultant_petition_login(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of consultant'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of consultant'),
            },
            ['email', 'password']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 1128, "token": "596eb25106662e018f8c75040264393e74ec9d96", "email": "abc@test.com",
                           "name": "Naksh Sharma", "petition": None}}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not Found', 'response': {"error": "User not found"}}
        }
    )(view_func)
    return decorated_view


def log1_consultant_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'api_key', 'description': 'API key of consultant', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'email', 'description': 'Email ID of consultant', 'type': openapi.TYPE_STRING, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"rate": 70, "feedback": [
                {"created_date": "2022-05-27T01:35:13.046782Z",
                 "description": "<p>Technically weak candidate. Weak in client side communication.</p>",
                 "name": "Rohit Jain"}], "location": "New York,NY", "status": "Project Terminated",
                                                                   "end_date": "2020-09-11", "start_date": "2020-06-01",
                                                                   "client": "Morgan Stanley",
                                                                   "job_title": "Java Developer", "is_remote": False,
                                                                   "marketer_name": "Mangesh Pathak",
                                                                   "work_type": "C2C"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view


def log1_consultant_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'api_key', 'description': 'API key of consultant', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'email', 'description': 'Email ID of consultant', 'type': openapi.TYPE_STRING, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 826, "project": {"id": 1081, "client_name": "Expedia", "vendor_name": "Bluehawk Consulting"},
                 "created_by": "Raj", "consultant": "Nishant Tomar", "tagged_user": [],
                 "feedback_type": "Engineering Issue", "department": "engineering",
                 "created": "2023-08-14T13:06:45.545855Z", "modified": "2023-08-14T13:06:45.548054Z",
                 "description": "Description of feedback", "rating": 4, "verdict": "Good"}], "count": 13}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)
    return decorated_view
