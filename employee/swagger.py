from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def register(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role of employee'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of employee'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone No. of employee'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee',
                                         enum=['male', 'female']),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee'),
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee id of employee'),
                'team': openapi.Schema(type=openapi.TYPE_STRING, description='Team of employee'),
            },
            [
                'role', 'name', 'email', 'phone', 'gender', 'password', 'employee_id', 'team'
            ],
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Success",
                                                         "data": {"id": 979, "employee_id": 9292923,
                                                                  "email": "demodemo@demo.com",
                                                                  "employee_name": "Demo Dev",
                                                                  "team": "Emeralds(Python)", "roles": ["engineer"],
                                                                  "gender": "male", "phone": "9393939494",
                                                                  "avatar": None, "is_superuser": False,
                                                                  "technology": None}}},
            400: {'description': 'Bad Request'},
            406: {'description': 'Already exists',
                  'response': {"message": "User already exist", "data": "admin@log1.com"}}
        }
    )(view_func)
    return decorated_view


def login(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee id of employee'),
                'fcm_token': openapi.Schema(type=openapi.TYPE_STRING, description='FCM token of employee'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee')
            },
            [
                'employee_id', 'password'
            ],
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"id": 1, "employee_id": 1000, "employee_name": "Consultadd Admin",
                         "email": "product@consultadd.com", "token": "78e44774510722e8ccbc7e52b8e01fa60622872e",
                         "team": "Product Team",
                         "roles": ["superadmin", "marketer", "engineer", "legal", "admin", "recruiter", "retention",
                                   "interviewee", "trainer", "hr", "finance", "management", "social_media", "business",
                                   "scrum_master"], "technology": ["Angular"], "shift": "afternoon",
                         "is_superuser": True}}},
            400: {'description': 'Bad Request',
                  'response': {"message": "Incorrect Password", "error": "Incorrect Password"}},
        }
    )(view_func)

    return decorated_view


def get_all_employees(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': "Filter data based on employee name", 'type': openapi.TYPE_STRING},
            {'name': 'teams', 'description': 'Team names (comma separated)', 'type': openapi.TYPE_STRING},
            {'name': 'type', 'description': 'Role of employee', 'type': openapi.TYPE_STRING},
            {'name': 'associate', 'description': 'Employee is associated to a team or not (default false)',
             'type': openapi.TYPE_BOOLEAN},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 488, "employee_id": 2853, "email": "aaditya.s@consultadd.com", "name": "Aaditya sohani"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_employee(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'roles': openapi.Schema(type=openapi.TYPE_STRING, description='Role of employee'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of employee'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone No. of employee'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee',
                                         enum=['male', 'female']),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee'),
                'employee_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'team': openapi.Schema(type=openapi.TYPE_STRING, description='Team of employee'),
                'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Employee is superuser or not'),
                'technology': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of name of technologies',
                                             items=openapi.Items(type=openapi.TYPE_STRING)),
                'avatar': openapi.Schema(type=openapi.TYPE_FILE, description='Profile picture of employee')
            },
            [],
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "result": {"id": 978, "employee_id": 10000, "email": "v@test.com", "employee_name": "Vi Test",
                           "team": "Elegant", "roles": ["superadmin", "admin", "marketer"], "gender": "male",
                           "phone": "9911111111", "avatar": None, "is_superuser": True, "technology": ["Python"]},
                "message": "User Updated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def account(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User id employee'),
                'active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Active status of employee'),
            },
            ['user_id', 'active'],
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Account Activated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def associated(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 4, "name": "Induci"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def bulk_register(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='csv or xlsx file containing detail of '
                                                                           'employees'),
            },
            ['file'],
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Success", "data": {
                "error": 1,
                "Failed": 2,
                "Created": 3,
                "Already Exist": 5,
            }}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def change_password(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'cur_password': openapi.Schema(type=openapi.TYPE_STRING, description='current password of employee'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='new password of employee')
            },
            ['cur_password', 'new_password'],
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "password updated"}},
            400: {'description': 'Success', 'response': {"message": "Wrong Password"}},
        }
    )(view_func)

    return decorated_view


def directory(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data by employee name or email', 'type': openapi.TYPE_STRING},
            {'name': 'team', 'description': 'To filter data based on team id', 'type': openapi.TYPE_INTEGER},
            {'name': 'roles', 'description': 'To filter data based on role id', 'type': openapi.TYPE_INTEGER},
        ],
        responses={

            200: {'description': 'Success', 'response': {"data": [
                {"id": 488, "employee_id": 2853, "email": "aaditya.s@consultadd.com", "employee_name": "Aaditya sohani",
                 "team": {"id": 56, "name": "Quartz(Java)", "dept": "Engineering",
                          "scrum_timing": "08:30 AM - 09:00 AM"}, "role": [{"id": 5, "name": "Engineer"}],
                 "account_login": True, "handover_to": None}]}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Access Denied', 'response': {"message": "You don't have access"}},
        }
    )(view_func)

    return decorated_view


def projects(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"project_id": 1289, "employer": "Consultadd", "consultant_name": "Niti Praveen",
                          "client": "Thompson, Zavala and Elliott", "vendor": "Garcia-Kennedy"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def logout(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success'}
        }
    )(view_func)

    return decorated_view


def me(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success', 'response': {
                "data": {"id": 1, "employee_id": 1000, "email": "product@consultadd.com",
                         "employee_name": "Consultadd Admin",
                         "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/1000.png",
                         "team": {"name": "Induci", "department": "Marketing"}, "gender": "male", "phone": "1234567890",
                         "roles": ["superadmin", "marketer", "engineer"], "shift": "general", "is_superuser": True,
                         "technology": ["Angular"], "handover": None, "project": None,
                         "display_roles": ["Superadmin", "Marketer", "Engineer"], "version": "R2023.5.1",
                         "have_certificate": True}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of employee'),
                'role_id': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of ids of roles',
                                          items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'team_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of team'),
            },
            ['user_id'],
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Aman Jain's Profile updated"}},
            400: {'description': 'Bad Request'},
            401: {'description': 'Access Denied', 'response': {"message": "You don't have access"}},
        }
    )(view_func)

    return decorated_view


def profile_activity(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'employee', 'description': 'ID of employee', 'type': openapi.TYPE_INTEGER, 'required': True}
        ],
        responses={

            200: {'description': 'Success', 'response': {"data": [
                {"id": 57169, "activity_type": "updated", "user_id": 1,
                 "desc": "Consultadd Admin changed Consultadd Admin's team ", "object_id": 1, "content_type_id": 14,
                 "created": "2023-01-13T14:14:13.813259Z"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def verify_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'vendor', 'description': 'Name of vendor company', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'client', 'description': 'Name of client company', 'type': openapi.TYPE_STRING, 'required': True},
            {'name': 'consultant', 'description': 'Name of consultant', 'type': openapi.TYPE_STRING, 'required': True}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1277, "employer": "Zioqu", "consultant_name": "Nisha Karki",
                 "client": "University of Washington", "vendor": "Team Red Dog"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def role(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 1, "name": "superadmin", "display_name": "Superadmin"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)


def shift_timings(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [["morning", "Morning Shift (6 AM to 3 PM)"]]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)


def team(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 2, "name": "Boto3"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)


def technology(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'technology': openapi.Schema(type=openapi.TYPE_STRING, description='Name of technology'),
            },
            ['technology'],
        ],
        responses={
            202: {'description': 'Bad Request', 'response': {"message": "Technologies Updated"}},
            400: {'description': 'Bad Request', 'response': {"message": "Input is empty"}},
        }
    )(view_func)

    return decorated_view


def update_user(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of employee'),
                'shift': openapi.Schema(type=openapi.TYPE_STRING, description='Shift detail of employee'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee'),
                'employee_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'team': openapi.Schema(type=openapi.TYPE_STRING, description='Team of employee'),
                'technology': openapi.Schema(type=openapi.TYPE_STRING, description='Name of technology'),
                'image': openapi.Schema(type=openapi.TYPE_FILE, description='Profile picture of employee'),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "User Profile Updated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def get_all_certificates(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"data": [
                {"id": 31, "certificate": {"name": "AWS Certified Cloud Practitioner", "organization": "Amazon"},
                 "created": "2023-01-25T12:37:48.149913Z", "modified": "2023-01-25T12:37:48.149918Z",
                 "has_expiry": False, "issued_date": "2023-01-01", "expiry_date": None, "credential_id": "",
                 "credential_url": None, "employee": 131}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_certificate(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'certificate_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of certificate'),
                'organization': openapi.Schema(type=openapi.TYPE_STRING, description='Issuer organization'),
                'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, description='Expiry date of certificate'),
                'issued_date': openapi.Schema(type=openapi.TYPE_STRING, description='Issue date of certificate'),
                'credential_id': openapi.Schema(type=openapi.TYPE_STRING, description='Credential ID of certificate'),
                'has_expiry': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Certificate has expiry date?'),
                'credential_url': openapi.Schema(type=openapi.TYPE_STRING, description='URl of credential'),
            },
            ['certificate_name', 'organization', 'issued_date', 'has_expiry']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Certificate Added"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_certificate(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'certificate_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of certificate'),
                'organization': openapi.Schema(type=openapi.TYPE_STRING, description='Issuer organization'),
                'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, description='Expiry date of certificate'),
                'issued_date': openapi.Schema(type=openapi.TYPE_STRING, description='Issue date of certificate'),
                'credential_id': openapi.Schema(type=openapi.TYPE_STRING, description='Credential ID of certificate'),
                'has_expiry': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Certificate has expiry date?'),
                'credential_url': openapi.Schema(type=openapi.TYPE_STRING, description='URl of credential'),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Certificate Info Updated"}},
            400: {'description': 'Bad Request', 'response': {"message": "Please provide correct certificate info"}},
        }
    )(view_func)

    return decorated_view


def mark_certificate(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'have_certificate': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                   description='Does employee has have certificate'),
            },
            ['have_certificate']
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": "Data updated successfully"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def get_all(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter certificate based on name', 'type': openapi.TYPE_STRING},
            {'name': 'organization', 'description': 'Does the certificate having an issuer organization',
             'type': openapi.TYPE_BOOLEAN},
            {'name': 'organization_name', 'description': 'To filter certificate based on organization name',
             'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 1, "name": "AWS Certified Cloud Practitioner", "issued_by": "Amazon"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def create_default_calender(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'emails': openapi.Schema(type=openapi.TYPE_ARRAY,
                                         description='List of emails you want to set to default',
                                         items=openapi.Items(type=openapi.TYPE_STRING)),
            },
            ['emails']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Emails set as default"}},
            400: {'description': 'Bad Request', 'response': {"message": "No emails provided to set set default"}},
        }
    )(view_func)

    return decorated_view


def default(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"aarti.b@consultadd.com": {
                "busy": [{"start": "2023-07-13T01:30:00-05:00", "end": "2023-07-13T02:00:00-05:00"}]}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def login_create_log1_user(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'log1_api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API Key of log1'),
                'team': openapi.Schema(type=openapi.TYPE_STRING, description='Name of team'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email ID of employee'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone no of employee'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee'),
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee ID of employee'),
                'keep_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Employee is active or not'),
                'role': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of role of employee',
                                       items=openapi.Items(type=openapi.TYPE_STRING))
            },
            ['log1_api_key', 'team', 'name', 'email', 'gender', 'password', 'employee_id']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "User Created in Log1", "user_id": 1000}},
            400: {'description': 'Bad Request'},
            401: {'description': 'Unauthorized', 'response': {"message": "Unauthorized"}},
        }
    )(view_func)

    return decorated_view


def login_create_bulk(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'log1_api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API Key of log1'),
                'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'log1': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Employee is active on log1 or '
                                                                                      'not'),
                        'role': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of role of employee',
                                               items=openapi.Items(type=openapi.TYPE_STRING)),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email ID of employee'),
                        'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone no of employee'),
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                        'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee',
                                                 default='male'),
                        'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee ID of employee'),
                        'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee',
                                                   default='consultadd'),
                        'team': openapi.Schema(type=openapi.TYPE_STRING, description='Team of employee'),
                    },
                    required=['log1', 'email', 'phone', 'name', 'employee_id', 'team']
                ), description='Data of employee'),
            },
            ['log1_api_key', 'data']
        ],
        responses={
            201: {'description': 'Success', 'response': {"result": {"users": [100], "msg": "1 users  Created"}}},
            400: {'description': 'Bad Request'},
            401: {'description': 'Unauthorized', 'response': {"message": "Unauthorized"}},
        }
    )(view_func)

    return decorated_view


def login_delete_employee(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'log1_api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API Key of log1'),
            },
            ['log1_api_key']
        ],
        responses={
            204: {'description': 'Success', 'response': {"message": "User Removed"}},
            400: {'description': 'Bad Request', 'response': {"message": "User not found"}},
            401: {'description': 'Unauthorized', 'response': {"message": "Unauthorized"}},
        }
    )(view_func)

    return decorated_view


def login_delete_bulk(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'log1_api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API Key of log1'),
                'users': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of employees',
                                        items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['log1_api_key', 'users']
        ],
        responses={
            204: {'description': 'Success', 'response': {"result": {"msg": "2 users  removed from beats"}}},
            400: {'description': 'Bad Request'},
            401: {'description': 'Unauthorized', 'response': {"message": "Unauthorized"}},
        }
    )(view_func)

    return decorated_view


def login_update_user(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'log1_api_key': openapi.Schema(type=openapi.TYPE_STRING, description='API Key of log1'),
                'team': openapi.Schema(type=openapi.TYPE_STRING, description='Name of team'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of employee'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email ID of employee'),
                'number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone no of employee'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender of employee'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of employee'),
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee ID of employee'),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Employee is active or not'),
                'role': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of role of employee',
                                       items=openapi.Items(type=openapi.TYPE_STRING))
            },
            ['log1_api_key']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": [{"id": 618,
                                                                   "password": "password",
                                                                   "last_login": "2023-03-07T16:29:37.323907Z",
                                                                   "username": "10001", "first_name": "",
                                                                   "last_name": "", "email": "rohit.p@consultadd.com",
                                                                   "is_staff": False, "is_active": False,
                                                                   "account_login": True, "is_superuser": False,
                                                                   "have_certificate": None, "employee_id": 10001,
                                                                   "date_joined": "2022-08-03T11:52:47Z",
                                                                   "employee_name": "ROHIT PAGARE", "slack_id": None,
                                                                   "phone": "918878888445",
                                                                   "avatar": "avatar/rohit_photo.jpg", "gender": "male",
                                                                   "shift": "evening", "team_id": 11,
                                                                   "technology": []}], "role": [{"id": 3,
                                                                                                 "name": "marketer",
                                                                                                 "display_name":
                                                                                                     "Marketer"}],
                                                         "result": "User updated on log1 successfully"}},
            400: {'description': 'Bad Request', 'response': {"message": "User not exists"}},
            401: {'description': 'Unauthorized', 'response': {"message": "Unauthorized"}},
        }
    )(view_func)

    return decorated_view


def handover_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of user'),
                'handover_to_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of handover user'),
            },
            ['user_id', 'handover_to_id']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "User handed over to Ravi Sharma"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': {"message": "You don't have permission to Handover"}},
        }
    )(view_func)

    return decorated_view


def handover_update(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'handover_to_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of handover user'),
            },
            ['handover_to_id']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "User handed over to Ravi Sharma"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': {"message": "You don't have permission to Handover"}},
            404: {'description': 'Not Found', 'response': {"message": "Handover not found"}},
        }
    )(view_func)

    return decorated_view


def handover_delete(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"message": "User handover removed"}},
            400: {'description': 'Bad Request', 'response': {"message": "User is not provided"}},
            403: {'description': 'Unauthorized', 'response': {"message": "You don't have permission to Handover"}},
            404: {'description': 'Not Found', 'response': {"message": "Handover not found"}},
        }
    )(view_func)

    return decorated_view


def handover_patch(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            405: {'description': 'Not Found', 'response': {"detail": "Method PATCH not allowed."}},
        }
    )(view_func)

    return decorated_view


def users_list(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter employees based on name', 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 569, "name": "Rahul Tailor", "type": "consultant"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def users_calendar_info(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'start', 'description': 'To filter based on start date', 'type': openapi.TYPE_STRING},
            {'name': 'end', 'description': 'To filter based on end date', 'type': openapi.TYPE_STRING},
            {'name': 'data', 'description': 'Data in JSON format (ex: {"emails":["a.t@test.com"]})',
             'type': openapi.TYPE_STRING, 'required': True},
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"a.t@test.com": {
                      "busy": [{"start": "2023-07-18T01:45:00-05:00", "end": "2023-07-18T02:15:00-05:00"}]}}}},
            400: {'description': 'Bad Request', 'response': {"message": "Please select user"}},
        }
    )(view_func)

    return decorated_view


def reset_password_token_request(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of employee'),
            },
            ['email']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Mail sent on a.b@test.com", "data": "mail sent"}},
            400: {'description': 'Bad Request', 'response': {"message": "Something went wrong"}},
        }
    )(view_func)

    return decorated_view


def reset_password_token_verify(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='OTP to reset password'),
            },
            ['token']
        ],
        responses={
            200: {'description': 'Success', 'response': {'message': 'OTP Verified'}},
            400: {'description': 'Bad Request', 'response': {'message': 'Invalid OTP'}},
        }
    )(view_func)

    return decorated_view


def reset_password_confirm_password(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='OTP to reset password'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Updated password of employee'),
            },
            ['token', 'password']
        ],
        responses={
            200: {'description': 'Success', 'response': {'message': 'Password changed successfully'}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view