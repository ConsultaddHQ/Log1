from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS, ERROR_MSG
from utils_app.utils import generate_swagger_auto_schema


def list_vendor_company(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': "This parameter is used to filter out the vendor company based on the company name.",
                'type': openapi.TYPE_STRING
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"id": 6169, "name": "CooperSurgical", "created_by": "2550 - Satyam Kumar Singh"}],
                "total": 94}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_vendor_company(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is the name of the vendor company which you want to create."
                ),

            },
            ['name', 'assign_to']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"data": {"id": 7802, "name": "Gammastack", "created_by": "3084 - Ritik Ratnawat"},
                               "message": "Vendor Company added"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def retrieve_vendor_contact(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 51118, "name": "Judith C", "email": "judith@chromedia.com", "number": "‪(720) 248-3667‬",
                 "company__name": "Chromedia Inc."},
                {"id": 48574, "name": "Ma. Judith Cabajar", "email": "abc@gmail.com", "number": "9987654132",
                 "company__name": "Chromedia Inc."},
                {"id": 46232, "name": "Ma. Judith Cabajar", "email": "judith@chromedia@gmail.com",
                 "number": "\t 720-336-1087", "company__name": "Chromedia Inc."},
                {"id": 46108, "name": "Ma. Judith Cabajar", "email": "Judith.cabajar@chromedia.com",
                 "number": "44344362127", "company__name": "Chromedia Inc."},
                {"id": 44993, "name": "Ma. Judith Kabajar", "email": "abc@gmail.com", "number": "0987654321",
                 "company__name": "Chromedia Inc."},
                {"id": 44939, "name": "Ma. Judith Cabajar", "email": "judithcab.ma@chromedia.com",
                 "number": "(636) 946-8497", "company__name": "Chromedia Inc."},
                {"id": 44757, "name": "Judith Cabajar", "email": "judith@chromedia.com", "number": "()",
                 "company__name": "Chromedia Inc."},
                {"id": 44458, "name": "Judith C", "email": "00", "number": "(732) 452-1006",
                 "company__name": "Chromedia Inc."}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_vendor_contact(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 35869, "name": "venkat guttula", "email": "venkat.guttula@testingxperts.com",
                 "number": "6803339575", "company__name": "Testing Xperts"},
                {"id": 34952, "name": "Venkat", "email": "venkat.guttula@testingxperts.com",
                 "number": "+1 680 333 9575", "company__name": "Testing Xperts"},
                {"id": 15034, "name": " Venkata Guttula", "email": "venkat.guttula@testingxperts.com",
                 "number": "(212) 389-9503 ", "company__name": "Testing Xperts"},
                {"id": 8318, "name": "Veerasankar Vanapalli", "email": "vanapalli.veerasankar@testingxperts.com",
                 "number": "(212) 389-9503", "company__name": "Testing Xperts"},
                {"id": 7976, "name": "Venkat", "email": "venkat.guttula@testingxperts.com", "number": "680-333-9575 ",
                 "company__name": "Testing Xperts"},
                {"id": 6985, "name": "Sudarshan Valeti", "email": "sudarsan.valeti@testingxperts.com",
                 "number": "915-2230268", "company__name": "Testing Xperts"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def create_vendor_contact(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is the email address of the person."
                ),
                'company': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is the unique ID of the vendor company."
                ),
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is the name of the person."
                ),
                'number': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is the contact number of the person."
                )

            },
            ['name', 'company', 'number']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 51124, "name": "Ravi Sharma", "email": "ravi@test1.com", "number": 9988990099},
                "message": "Vendor Contact created"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_lead(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': "This parameter is used to filter the list by city name, job title, or vendor company.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'sort_by',
                'description': "This parameter is used to sort the list according to created date or modified date.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': "This parameter is a JSON which will filter the list by status, position, and vendor.",
                'type': openapi.TYPE_OBJECT
            }
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"counts": {"total": 11, "new": 3, "sub": 8, "draft": 0, "archive": 0}, "data": [
                      {"id": 1825, "job_desc": "Workday financial reporting", "city": "Aaronsburg,PA",
                       "job_title": "workday consultant", "primary_skill": "Workday", "is_w2": False, "status": "new",
                       "created": "2019-08-29T14:52:16.934000Z", "modified": "2019-08-29T14:52:16.940000Z",
                       "position_type": "c2c", "company_id": 1224, "submission_count": 0, "company_name": "Samcore Inc",
                       "position_name": None}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def retrieve_lead(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"id": 62775, "job_desc": "All the descriptions are added in the pdf",
                                        "city": "Aaronsburg,PA", "job_title": "Data analyst", "primary_skill": None,
                                        "is_w2": False, "status": "new", "created": "2022-12-19T15:44:37.916356Z",
                                        "modified": "2022-12-19T15:44:37.931234Z", "position_type": "full_time",
                                        "company_id": 3422, "submission_count": 0, "company_name": "Testing Xperts",
                                        "position_name": "Data Analyst"}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def create_lead(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'is_w2': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="This parameter is for whether the requirement is of 'W2' type or not."
                ),
                'job_desc': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the job description of the requirement."
                ),
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the city of the requirement."
                ),
                'job_title': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the job title of the requirement."
                ),
                'primary_skill': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the primary skill of the consultant."
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the current status of the requirement."
                ),
                'position_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the type of position that the requirement has (e.g., full-time, part-time)."
                ),
                'secondary_skills': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="This parameter is for the secondary skills of the consultant.",
                    items=openapi.Items(type=openapi.TYPE_STRING)
                ),
                'position': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the ID of the position."
                ),
                'vendor_company': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the ID of the vendor company."
                ),
                'owner': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the person who has created the requirement."
                ),
                'shared_to': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="This parameter is for the group of people who are connected to this requirement.",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                )
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 73252, "job_desc": "Node js Developer required", "city": "Yabucoa,PR",
                         "job_title": "Backend developer", "primary_skill": "Node.js", "is_w2": True, "status": "sub",
                         "created": "2023-09-08T09:06:12.799111Z", "modified": "2023-09-08T09:06:12.814969Z",
                         "position_type": "full_time", "company_id": 3422, "submission_count": 0,
                         "company_name": "Testing Xperts", "position_name": "Full Stack Node Developer"},
                "message": "Requirement added"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def update_lead(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'is_w2': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="This parameter is for whether the requirement is of 'W2' type or not."
                ),
                'job_desc': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the job description of the requirement."
                ),
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the city of the requirement."
                ),
                'job_title': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the job title of the requirement."
                ),
                'primary_skill': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the primary skill of the consultant."
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the current status of the requirement."
                ),
                'position_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="This parameter is for the type of position that the requirement has (e.g., full-time, part-time)."
                ),
                'secondary_skills': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="This parameter is for the secondary skills of the consultant.",
                    items=openapi.Items(type=openapi.TYPE_STRING)
                ),
                'position': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the ID of the position."
                ),
                'vendor_company': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the ID of the vendor company."
                ),
                'owner': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="This parameter is for the person who has created the requirement."
                ),
                'shared_to': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="This parameter is for the group of people who are connected to this requirement.",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                )
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 73252, "job_desc": "Node js Developer required", "city": "Yabucoa,PR",
                         "job_title": "Full stack Developer", "primary_skill": "Node.js", "is_w2": True,
                         "status": "sub", "created": "2023-09-08T09:06:12.799111Z",
                         "modified": "2023-09-08T09:18:12.810264Z", "position_type": "full_time", "company_id": 3422,
                         "submission_count": 0, "company_name": "Testing Xperts",
                         "position_name": "Full Stack Node Developer"}, "message": "Requirement updated"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS},
            404: {"message": "Requirement not found"}
        }
    )(view_func)

    return decorated_view


def destroy_lead(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success'},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def lead_fields(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": ["is_w2", "job_desc"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def lead_get_archived(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'sort_by',
                'description': "This parameter is used to sort the list according to created date or modified date.",
                'type': openapi.TYPE_STRING
            },
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": [
                      {"id": 8143, "job_desc": "job desc", "city": "San Jose,CA", "job_title": "Workday HCM consultant",
                       "primary_skill": "Workday", "is_w2": False, "status": "archived",
                       "created": "2020-02-24T16:08:00.505366Z", "modified": "2020-02-24T16:09:35.089589Z",
                       "position_type": "c2c", "company_id": 142, "submission_count": 0,
                       "company_name": "Compunnel Software Group Inc", "position_name": None}],
                      "counts": {"total": 72835, "new": 1241, "sub": 71503, "draft": 14, "archive": 77}}},
            400: {'description': 'Bad Request'}
        },
        methods=['get']
    )(view_func)

    return decorated_view


def lead_put_archived(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'lead_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="This parameter is the list of ids of the leads whom we want to archive",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                )
            },
            ['lead_ids']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Requirement Archived"}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)

    return decorated_view


def retrieve_v2_submission(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"id": 29329, "lead": {"id": 28143,
                                                              "job_desc": "Our Team Adaptive Insights, a Workday Company, is building out one of their newest teams, Data Management. This highly visible team is responsible for moving our enterprise SaaS application into a modern and scalable database solution.\nThe Role\nWe are looking for a creative and motivated server-side engineer with good database development experience. Required Skills:\n• 5+ years of software development and database experience\n\n• Expert in Python coding skills\n\n• Experience with Postgres and/or NoSQL Databases (Cassandra, MongoDB, Couchbase)\n\n• Experience in Oracle Database\n\n• Experience in PL/SQL, SQL, Stored procedures and Java\n\n• Experience with distributed systems, fault-tolerance, redundancy, and SQL performance\n\n• BS/MS in Computer Science, Engineering, or related field preferred",
                                                              "job_title": "Python Developer",
                                                              "primary_skill": "Python", "city": "Remote,US",
                                                              "vendor_company_id": 2678,
                                                              "vendor_company_name": "TEKsystems",
                                                              "owner": "Shaban Khan", "status": "sub",
                                                              "created": "2020-09-15T19:44:26.657409Z",
                                                              "modified": "2020-09-15T19:44:26.803173Z", "is_w2": False,
                                                              "position_name": None, "position_type": "C2C"},
                                        "rate": 0.0, "client": "N/A", "employer": "Garuda",
                                        "email": "sanjayranjit881@gmail.com", "phone": "(405) 500-5314",
                                        "status": "interview", "is_active": True, "vendor_contact": None,
                                        "marketer_name": "Shaban Khan", "is_complete": True, "vendor_layer": [],
                                        "work_type": "C2C"}, "permission": {"update": False}}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_tabs(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"data": {"test": False, "project": False, "interview": True}}}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_fields(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {
                      "data": ["is_w2", "job_desc", "city", "secondary_skills", "position", "employer", "rate", "email",
                               "client", "phone", "requirement_type"]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_documents(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [
                      {"id": 39493, "object_id": 29310, "attachment_type": "resume", "file_name": "abhi.docx",
                       "type": {"name": "resume", "display_name": "Resume"}}]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_profile(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"id": 201, "name": "Ankur Pathania", "email": "ankur.pathania2990@gmail.com",
                                        "current_city": "California", "phone_no": "(408) 478-9065",
                                        "status": "on_project",
                                        "profile": {"linkedin": "http://www.linkedin.com/in/ankurpathania2990/",
                                                    "visa_end": "2024-08-31",
                                                    "education": "Doctor of Business Administration ",
                                                    "visa_type": "gc",
                                                    "other_link": "http://www.linkedin.com/in/ankurpathania2990/",
                                                    "visa_start": "2022-09-01", "current_city": "California",
                                                    "date_of_birth": "1990-09-02", "marketer": "Consultadd Admin"}}}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_activities(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 79898,
                                         "user": {"id": 1, "employee_id": 1000, "email": "product@consultadd.com",
                                                  "employee_name": "Consultadd Admin", "team": "Product Team",
                                                  "roles": ["superadmin", "marketer", "engineer", "legal"],
                                                  "gender": "male", "phone": "1234567890", "avatar": "avatar",
                                                  "technology": ["Angular"]}, "activity_type": "created",
                                         "desc": "Consultadd Admin added submission", "object_id": 75608,
                                         "created": "2023-08-01T11:02:43.700223Z", "content_type": 34}]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_resume(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [
                      {"id": 45806, "object_id": 33333, "attachment_type": "resume", "file_name": "Sanjay.docx",
                       "type": {"name": "resume", "display_name": "Resume"}}], "visibility": True, "status": "sub"}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_employer(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 28, "name": "Account Management"}, {"id": 2, "name": "Boto3"},
                                        {"id": 1, "name": "Consultadd"}, {"id": 41, "name": "Consultadd Canada"},
                                        {"id": 59, "name": "Elegant"}, {"id": 3, "name": "Elegant Team"},
                                        {"id": 60, "name": "Elegantc"}, {"id": 4, "name": "Induci"},
                                        {"id": 5, "name": "Ioneq"}, {"id": 26, "name": "JLA"},
                                        {"id": 6, "name": "NetResolute"}, {"id": 8, "name": "OC10"},
                                        {"id": 10, "name": "Pythonwise"}, {"id": 11, "name": "Zioqu"}]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_interviews(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [
                      {"id": 4663, "supervisor": {"call_given_by": "Interviewee", "supervisor_name": "Ritu Soni"},
                       "guest": [], "permission": {"update": False}, "marketer_name": "Satyam Kumar Singh",
                       "guest_feedback": None, "attachment_link": None, "allow_status_change": True,
                       "supervisor_feedback": None, "created": "2021-04-13T21:48:10.481187Z",
                       "modified": "2021-05-05T13:35:24.280747Z", "round": 1,
                       "feedback": "Interviewer caught us mimicking", "guest_remark": None, "coding_present": None,
                       "end_time": "2021-04-14T16:45:59Z", "notes": None, "coding_info": None, "description": "",
                       "guest_type": None, "start_time": "2021-04-14T16:00:51Z", "call_details": "Zoom",
                       "tech_stack": None, "screening_type": "vendor_screening", "interview_mode": "video_call",
                       "status": "failed", "if_previous_calendar": True, "failure_reason": ["caught_mimicking"],
                       "passed_reason": None, "submission": 42079}]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_tests(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [
                      {"id": 2308, "status": "new", "deadline": "2023-08-22", "is_offline": True, "feedback": None,
                       "link": "", "additional_details": "Testing", "submit_date": None, "engineer_remarks": None,
                       "is_video": False, "skills": ["C#"], "engineers": None, "submitted_by": None,
                       "created": "2023-08-22T06:40:37.755816Z", "attachments": [], "cancel_reason": None,
                       "assigned_to": [], "permission": {"update": True}, "engineer_feedback": [],
                       "platform": "Amcat"}]}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_support(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"data": [{"id": 172, "support": {"id": 249, "email": "snehal.b@consultadd.com",
                                                                         "employee_name": "Snehal Dinkar Barge"},
                                                  "status": None, "created": "2020-08-14T21:12:32.380711Z",
                                                  "modified": "2020-08-16T12:07:57.840349Z",
                                                  "feedback": "She is co-operative and doing well. Independent.",
                                                  "end": "2022-12-08", "start": "2020-04-20", "is_proxy_support": False,
                                                  "project": 311}, {"id": 78, "support": {"id": 233,
                                                                                          "email": "shreya.s@consultadd.com",
                                                                                          "employee_name": "Shreya Soni"},
                                                                    "status": None,
                                                                    "created": "2020-08-12T20:51:16.222040Z",
                                                                    "modified": "2020-08-12T20:53:00.704828Z",
                                                                    "feedback": "Switched to remote project.",
                                                                    "end": "2022-12-08", "start": "2020-03-16",
                                                                    "is_proxy_support": False, "project": 311}],
                                        "project": 311}}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def v2_submission_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"id": 311, "status": "complete", "feedback": "",
                                        "check_list": {"total": 6, "msa": 1, "work_order": 1, "status": True,
                                                       "msa_signed": 1, "start_date": 1, "client_address": 1,
                                                       "vendor_address": 1, "work_order_signed": 1,
                                                       "reporting_details": 1}, "attachments": [
                          {"id": 79453, "file_name": "Updated_Third_Party_SOW_-_Banda.doc.pdf",
                           "attachment_type": "work_order",
                           "type": {"name": "work_order", "display_name": "Work Order"}},
                          {"id": 11275, "file_name": "PO__MrjLGJW.pdf", "attachment_type": "msa_signed",
                           "type": {"name": "msa_signed", "display_name": "MSA/Agreement Signed"}},
                          {"id": 11274, "file_name": "Banda_Sushmita_-_Contractors_Agreement-Countersigned.pdf",
                           "attachment_type": "work_order_signed",
                           "type": {"name": "work_order_signed", "display_name": "Work Order Signed"}},
                          {"id": 11232, "file_name": "Banda_Sushmita_-_Contractors_Agreement_RIka2YL.pdf",
                           "attachment_type": "msa", "type": {"name": "msa", "display_name": "MSA/Agreement"}},
                          {"id": 11231, "file_name": "PO__ppn3BSM.pdf", "attachment_type": "work_order",
                           "type": {"name": "work_order", "display_name": "Work Order"}},
                          {"id": 11230, "file_name": "Banda_Sushmita_-_Contractors_Agreement.pdf",
                           "attachment_type": "msa", "type": {"name": "msa", "display_name": "MSA/Agreement"}},
                          {"id": 11229, "file_name": "PO_.pdf", "attachment_type": "work_order",
                           "type": {"name": "work_order", "display_name": "Work Order"}}],
                                        "created": "2020-03-03T18:25:08.619484Z", "city": "Boulder,CO",
                                        "remote_consultant": {"id": 129, "name": "Sushmitha Banda"}, "duration": "3",
                                        "invoicing_period": 30,
                                        "client_address": "2477 55th St, Boulder, CO 80301, United States",
                                        "vendor_address": "Northbrook, IL", "payment_term": 30,
                                        "start_date": "2020-03-16", "end_date": "2022-10-14", "rate": 80.0,
                                        "employer": "consultadd", "reporting_details": "Not received yer",
                                        "is_remote": False, "permission": {"update": True}}}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def list_submission(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': "This parameter is used to filter the list by client company, lead city, etc.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'sort_by',
                'description': "This parameter is used to sort the list according to created date or modified date.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_for',
                'description': "This parameter is used to filter the list according to submissions made by me, my team, or all.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': "This parameter is a JSON object that will filter the list by status, client, teams, incomplete, marketer, vendor, and consultant.",
                'type': openapi.TYPE_OBJECT,
                'properties': {
                    'status': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by status."
                    ),
                    'client': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by client."
                    ),
                    'teams': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by teams."
                    ),
                    'incomplete': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by incomplete."
                    ),
                    'marketer': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by marketer."
                    ),
                    'vendor': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by vendor."
                    ),
                    'consultant': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Filter by consultant."
                    )
                }
            },
            {
                'name': 'export',
                'description': "This parameter is a boolean parameter used to check whether the user wants to export the list or not.",
                'type': openapi.TYPE_BOOLEAN
            },
            {
                'name': 'filter_by_status',
                'description': "This parameter is used to filter the list by status.",
                'type': openapi.TYPE_STRING
            }
        ],

        responses={
            200: {'description': 'Success',
                  'response': {"counts": {"total": 13559, "sub": 13151, "project": 88, "interview": 315}, "data": [
                      {"id": 79220, "client": "", "employer": "Consultadd", "status": "sub",
                       "created": "2023-07-29T05:39:47.285569Z", "modified": "2023-07-29T05:39:47.391858Z", "rate": 0,
                       "is_active": False, "project": None, "vendor_contact": 40434, "is_complete": False,
                       "work_type": "c2c", "city": "Remote,US", "marketer_id": 1,
                       "company_name": "Placeholder-Remote Vendor", "marketer_name": "Consultadd Admin",
                       "consultant_name": "Ekta J Patel"}], "url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def submission_create(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'position': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the lead."
                ),
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="City name of the lead."
                ),
                'job_desc': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Job description of the lead."
                ),
                'position_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Position type of lead."
                ),
                'vendor_company': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the vendor company."
                ),
                'profile_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the consultant's profile."
                ),
                'vendor_contact': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the contact person of the vendor company."
                ),
                'rate': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Rate of the lead."
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Email ID of the consultant."
                ),
                'phone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Phone number of the consultant."
                ),
                'client': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the client company."
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the employer."
                ),
                'work_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Work Type of the lead."
                ),
                'marketing_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Marketing ID of the consultant."
                ),
                'marketing_team_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the marketing team."
                ),
                'file_resume': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Resume file of the consultant."
                ),
                'file_other': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Other files of the consultant."
                )

            },
            ['position', 'city', 'job_desc', 'position_type', 'vendor_company', 'profile_id', 'vendor_contact', 'rate',
             'email', 'phone', 'client', 'employer', 'work_type', 'marketing_id', 'marketing_team_id', 'file_resume',
             'file_other']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"data": {"id": 79247, "status": "sub", "created": "2023-09-08T11:33:42.193136Z",
                                        "modified": "2023-09-08T11:33:42.209242Z", "consultant_id": 201,
                                        "consultant_name": "Ankur Pathania", "attachments": []},
                               "message": "Submission created"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def update_submission(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'position': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the lead."
                ),
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="City name of the lead."
                ),
                'job_desc': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Job description of the lead."
                ),
                'position_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Position type of lead."
                ),
                'vendor_company': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the vendor company."
                ),
                'profile_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the consultant's profile."
                ),
                'vendor_contact': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the contact person of the vendor company."
                ),
                'rate': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Rate of the lead."
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Email ID of the consultant."
                ),
                'phone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Phone number of the consultant."
                ),
                'client': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the client company."
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the employer."
                ),
                'work_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Work Type of the lead."
                ),
                'marketing_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Marketing ID of the consultant."
                ),
                'marketing_team_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the marketing team."
                ),
                'file_resume': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Resume file of the consultant."
                ),
                'file_other': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Other files of the consultant."
                )

            },
            []
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"id": 37940, "created": "2021-01-13T19:45:55.137416Z",
                                        "modified": "2023-09-08T11:37:58.757301Z", "rank": 0, "employer": "Induci",
                                        "rate": 40.0, "is_active": True, "is_complete": True,
                                        "email": "abhishek1@test.com", "client": "TCS", "phone": "18765456783",
                                        "status": "sub", "work_type": "w2", "visa_end": "2021-06-30",
                                        "visa_start": "2020-07-18", "education": None, "visa_type": "opt",
                                        "linkedin": None, "other_link": "", "date_of_birth": "1991-09-09",
                                        "current_city": "Edmond,OK", "lead": 36677, "consultant_marketing": 719,
                                        "vendor_contact": 24273, "created_by": 195, "marketing_team": 14},
                               "message": "Submission updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def submission_feedback_due(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success',
                  'response': {"marketer_feedback_due": True}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def submission_feedback_check(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"test": False, "interview": False}}},
            400: {'description': 'Bad Request'},
            403: {'description': {"message": "Submission not found"}}
        }
    )(view_func)

    return decorated_view


def submission_resume(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Resume to upload"
                ),

            },
            ['file']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"id": 75607, "object_id": 1168, "attachment_type": "test_submit",
                                        "file_name": "data.csv",
                                        "type": {"name": "test_submit", "display_name": "Test Submission Docs"}},
                               "message": "Resume updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def submission_suggestions(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'client_name',
                'description': "This parameter is the name of the client company.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'consultant',
                'description': "This parameter is the ID of the consultant.",
                'type': openapi.TYPE_INTEGER
            },
            {
                'name': 'lead_id',
                'description': "This parameter is the ID of the lead.",
                'type': openapi.TYPE_INTEGER
            },
            {'name': 'company_id',
             'description': "This parameter is the ID of the lead.",
             'type': openapi.TYPE_INTEGER
             },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 68366, "client": "Apple", "created": "2023-02-09T19:52:50.445199Z", "status": "sub",
                 "city": "Remote,US", "job_title": "Java developer", "company_name": "Innova Solutions",
                 "marketer_name": "Vishal Choudhary", "consultant_name": "Ayushi Nigam"}], "total": 58}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def submission_did_you_mean(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'client',
                'description': "This parameter is the name of the client company.",
                'type': openapi.TYPE_STRING,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": ["Persistent Systems"]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def submission_client(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': "This parameter is the name of the client company.",
                'type': openapi.TYPE_STRING,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": ["Google", "Google Ads"]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def submission_work_type(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [["c2c", "C2C"], ["w2", "W2(Contract)"], ["full_time", "Full Time"]]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)
    return decorated_view


def submission_similar_submission(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'client',
                'description': 'This parameter is the name of the client company.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'consultant_id',
                'description': 'This parameter is the ID of the consultant.',
                'type': openapi.TYPE_INTEGER
            },
            {
                'name': 'lead_id',
                'description': 'This parameter is the ID of the lead.',
                'type': openapi.TYPE_INTEGER
            },
            {
                'name': 'filter_by',
                'description': 'This parameter is used to filter submissions by client company or vendor company.',
                'type': openapi.TYPE_STRING
            }

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"created": "2023-09-08T12:05:37.811297Z", "status": "sub", "client": "google", "id": 79248,
                 "marketer_name": "Gufran Am", "consultant_name": "Bharat Bhate", "vendor_company": "Persistant"}],
                "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def retrieve_vendor_layer(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 602, "vendor_company": {"id": 8, "name": "google", "created_by": None},
                 "created": "2023-08-01T12:45:21.450507Z", "modified": "2023-08-01T12:45:21.450511Z", "level": 1,
                 "submission": 75624}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_vendor_layer(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of submission"
                ),
                'company': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of company"
                ),
            },
            ['submission', 'company']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"data": {"id": 611, "vendor_company": {"id": 8, "name": "google", "created_by": None},
                                        "created": "2023-09-08T12:15:06.704173Z",
                                        "modified": "2023-09-08T12:15:06.704177Z", "level": 3, "submission": "75624"},
                               "message": "Vendor layer added"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_vendor_layer(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'data': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="List of ID's of vendor layer",
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                ),

            },
            ['data']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Vendor layer updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def destroy_vendor_layer(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success'},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def retrieve_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 9269, "allow_status_change": True,
                                                                  "submission": {"id": 71800,
                                                                                 "created": "2023-03-27T17:44:22.683697Z",
                                                                                 "modified": "2023-04-24T13:01:30.756189Z",
                                                                                 "rank": 1, "employer": "Consultadd",
                                                                                 "rate": 70.0, "is_active": False,
                                                                                 "is_complete": True,
                                                                                 "email": "r1899rohit@gmail.com",
                                                                                 "client": "Huntington Bank",
                                                                                 "phone": "16464509124",
                                                                                 "status": "project",
                                                                                 "work_type": "c2c",
                                                                                 "visa_end": "2024-09-30",
                                                                                 "visa_start": "2021-10-01",
                                                                                 "education": "", "visa_type": "h1b",
                                                                                 "linkedin": None, "other_link": None,
                                                                                 "date_of_birth": "1994-01-08",
                                                                                 "current_city": "Charlotte,NC",
                                                                                 "lead": 69633,
                                                                                 "consultant_marketing": 1582,
                                                                                 "vendor_contact": 47726,
                                                                                 "created_by": 665,
                                                                                 "marketing_team": 8}, "guest": [
                    {"id": 963, "employee_id": 10089, "email": "ashwin.d@consultadd.com",
                     "employee_name": "Ashwin Dhangar", "team": "Consultadd", "roles": ["engineer"], "gender": "Male",
                     "phone": "6263576023", "avatar": None, "is_superuser": False, "technology": None},
                    {"id": 387, "employee_id": 2727, "email": "ayush.b@consultadd.com",
                     "employee_name": "Ayush Bendwal", "team": "Epimonis", "roles": ["engineer"], "gender": "male",
                     "phone": "917000190424",
                     "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/A704208A-169F-453B-A097-EDD335F70CF5.jpg",
                     "is_superuser": False,
                     "technology": ["Nodejs", "JavaScript", "ReactJS", "Python", "AWS", "Full Stack", "Java", "SQL",
                                    "DevOps", "Django", "MERN", "React"]},
                    {"id": 482, "employee_id": 2854, "email": "piyush.j@consultadd.com",
                     "employee_name": "Piyush Joshi", "team": "Jaspers(Java)", "roles": ["engineer"], "gender": "male",
                     "phone": "919993585581",
                     "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/8065.png",
                     "is_superuser": False, "technology": ["Java", "JavaScript", "Angular", "SQL"]},
                    {"id": 643, "employee_id": 10007, "email": "yashraj.m@consultadd.com",
                     "employee_name": "YASHRAJ MANDLOI", "team": "Kynites(Java)", "roles": ["engineer"],
                     "gender": "male", "phone": "918770160192", "avatar": None, "is_superuser": False,
                     "technology": ["Java"]}], "supervisor": {"id": 131, "employee_id": 2164,
                                                              "email": "ankit.p@consultadd.com",
                                                              "employee_name": "Ankit Pathak", "team": "GoKronos",
                                                              "roles": ["interviewee"], "gender": "male",
                                                              "phone": "1234567890",
                                                              "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/2164.png",
                                                              "is_superuser": False, "technology": None},
                                                                  "created": "2023-03-27T19:59:03.984640Z",
                                                                  "modified": "2023-03-29T19:27:44.992183Z", "round": 1,
                                                                  "feedback": "We got a call from the vendor immediately after the interview was over.",
                                                                  "guest_remark": "All questions are related to debugging or explaining angular code where the first one is related to finding differences between two functions, In the second question we need to describe the use of a callable interface in js in code, on the question is related to routing in angular with lazy loading and load children, overall went well we were able to answer all of them ",
                                                                  "coding_present": True,
                                                                  "end_time": "2023-03-28T15:00:41Z", "notes": None,
                                                                  "coding_info": "", "description": "",
                                                                  "guest_type": "assigned",
                                                                  "start_time": "2023-03-28T14:00:41Z",
                                                                  "call_details": "", "tech_stack": "Angular,.NET",
                                                                  "attachment_link": None,
                                                                  "screening_type": "interview",
                                                                  "interview_mode": "video_call", "status": "offer",
                                                                  "if_previous_calendar": False, "failure_reason": None,
                                                                  "passed_reason": None},
                                                         "permission": {"update": False}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'Some string or number by which you want to filter data.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_for',
                'description': 'This parameter is used to filter the data based on me, my team, handover, all.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': 'This is a JSON containing various parameters by which you can filter the data.',
                'type': openapi.TYPE_OBJECT
            },
            {
                'name': 'sort_by',
                'description': 'This parameter is used to sort the data on dates (created, modified, start time).',
                'type': openapi.TYPE_STRING
            }

        ],
        responses={
            200: {'description': 'Success', 'response': {
                "counts": {"total": 1, "offer": 1, "failed": 0, "scheduled": 0, "cancelled": 0, "next_round": 0,
                           "rescheduled": 0, "feedback_due": 0}, "data": [{"id": 9269, "guest": [
                    {"id": 963, "name": "Ashwin Dhangar", "email": "ashwin.d@consultadd.com"},
                    {"id": 643, "name": "YASHRAJ MANDLOI", "email": "yashraj.m@consultadd.com"}],
                                                                           "submission": {"id": 71800,
                                                                                          "client": "Huntington Bank",
                                                                                          "marketer_id": 665,
                                                                                          "work_type": "c2c",
                                                                                          "job_title": "Dot net Developer",
                                                                                          "marketer_name": "Jasraj Singh Hora",
                                                                                          "vendor": "TEKsystems",
                                                                                          "project": True,
                                                                                          "position_name": "Dot Net Developer"},
                                                                           "consultant_name": "Rohit Shrivastava",
                                                                           "supervisor_detail": {
                                                                               "call_given_by": "Interviewee",
                                                                               "supervisor_name": "Ankit Pathak"},
                                                                           "supervisor_feedback": True,
                                                                           "allow_status_change": True,
                                                                           "created": "2023-03-27T19:59:03.984640Z",
                                                                           "modified": "2023-03-29T19:27:44.992183Z",
                                                                           "round": 1, "feedback": "feedback",
                                                                           "guest_remark": "remark ",
                                                                           "coding_present": True,
                                                                           "end_time": "2023-03-28T15:00:41Z",
                                                                           "coding_info": "", "guest_type": "assigned",
                                                                           "start_time": "2023-03-28T14:00:41Z",
                                                                           "tech_stack": "Angular,.NET",
                                                                           "screening_type": "interview",
                                                                           "interview_mode": "video_call",
                                                                           "status": "offer",
                                                                           "if_previous_calendar": False,
                                                                           "failure_reason": None,
                                                                           "passed_reason": None}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def interview_export(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'Some string or number by which you want to filter data.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_for',
                'description': 'This parameter is used to filter the data based on me, my team, handover, all.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': 'This is a JSON containing various parameters by which you can filter the data.',
                'type': openapi.TYPE_OBJECT
            },
            {
                'name': 'sort_by',
                'description': 'This parameter is used to sort the data on dates (created, modified, start time).',
                'type': openapi.TYPE_STRING
            }

        ],
        responses={
            200: {'description': 'Success', 'response': """Interview Id,Consultant Name,Marketer Name,Supervisor Name,Client Name,Vendor Name,Round,Scheduled At,Mode,Screening Type,Tech Stack,Status,Failure Reason,Passed Reason
9269,Rohit Shrivastava,Jasraj Singh Hora,Ankit Pathak(Interviewee),Huntington Bank,TEKsystems,1,2023-03-28T14:00:41Z,video_call,interview,"Angular,.NET",offer,,
"""},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def interview_export_detail(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'Some string or number by which you want to filter data.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_for',
                'description': 'This parameter is used to filter the data based on me, my team, handover, all.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': 'This is a JSON containing various parameters by which you can filter the data.',
                'type': openapi.TYPE_OBJECT
            },
            {
                'name': 'sort_by',
                'description': 'This parameter is used to sort the data on dates (created, modified, start time).',
                'type': openapi.TYPE_STRING
            }

        ],
        responses={
            200: {'description': 'Success', 'response': """application/textInterview Id,Interview Time,Marketer Name,Consultant Name,Work Auth,Supervisor,Job Title,Client,Vendor,Interview Status,Interview Feedback,Failure Reason,Coding Present,Coders,Supervisor Remark,Coders Remark,Supervisor Feedback,Coder Feedback
9269,"Mar 28, 2023, 02 PM",Jasraj Singh Hora,Rohit Shrivastava,H-1B,Ankit Pathak,Dot net Developer,Huntington Bank,TEKsystems,offer,We got a call from the vendor immediately after the interview was over.,,True,"Ashwin Dhangar, Ayush Bendwal, Piyush Joshi, YASHRAJ MANDLOI",call went well,"All questions are related to debugging or explaining angular code where the first one is related to finding differences between two functions, In the second question we need to describe the use of a callable interface in js in code, on the question is related to routing in angular with lazy loading and load children, overall went well we were able to answer all of them ","(Q)Was coding involved in call ---> Yes, (Q)Were we able to code ---> Yes, (Q)What went well in call ---> Coding on time, Good Mimicking, Complete details from Marketer, (Q)Issues faced during call ---> None, (Q)Is it a final round ---> Yes, (Q)Offer Probability ---> 10, (Q)Overall Call Rating ---> Good, (Q)Remark ---> call went well","(Q)Coding Language? ---> Angular, (Q)How many question were there? ---> 4, (Q)Were you able to solve the questions? ---> yes"
"""},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the submission."),
                'supervisor': openapi.Schema(type=openapi.TYPE_INTEGER,
                                             description="ID of the supervisor of the interview."),
                'interview_mode': openapi.Schema(type=openapi.TYPE_STRING,
                                                 description="It is the mode in which the interview happened (e.g., Webex, Hangout)."),
                'screening_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                 description="This parameter tells which type of screening this is (e.g., IP Tech Screening, Vendor Tech Screening, Interview)."),
                'description': openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Any additional description will be put here."),
                'start_time': openapi.Schema(type=openapi.TYPE_STRING, description="Start time of the interview."),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, description="End time of the interview."),
                'guest': openapi.Schema(type=openapi.TYPE_ARRAY,
                                        description="List of users who will be guests of the interview.",
                                        items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'call_details': openapi.Schema(type=openapi.TYPE_STRING, description="Details related to the call."),
                'guest_type': openapi.Schema(type=openapi.TYPE_STRING,
                                             description="Which type of guest is the person."),
                'tech_stack': openapi.Schema(type=openapi.TYPE_STRING,
                                             description="What is the tech stack required in the interview."),
                'coding_info': openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Whether coding is required or not.")
            },

            ['submission', 'start_time', 'end_time']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {
                      "data": {"id": 9569, "round": 1, "status": "scheduled", "start_time": "2023-06-09T20:00:00Z",
                               "end_time": "2023-06-09T21:00:00Z", "screening_type": "interview",
                               "submission_id": 33333, "interview_mode": "video_call", "rank": 1, "client": "N/A",
                               "job_title": "AWS Developer", "supervisor_name": "Bharat Bhate",
                               "company_name": "Pyramid Consulting", "marketer_name": "Shaban Khan",
                               "consultant_name": "Sanjay Ranjit"}, "booking_response": "booked",
                      "message": "Interview created"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the submission."),
                'supervisor': openapi.Schema(type=openapi.TYPE_INTEGER,
                                             description="ID of the supervisor of the interview."),
                'interview_mode': openapi.Schema(type=openapi.TYPE_STRING,
                                                 description="It is the mode in which the interview happened (e.g., Webex, Hangout)."),
                'screening_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                 description="This parameter tells which type of screening this is (e.g., IP Tech Screening, Vendor Tech Screening, Interview)."),
                'description': openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Any additional description will be put here."),
                'start_time': openapi.Schema(type=openapi.TYPE_STRING, description="Start time of the interview."),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, description="End time of the interview."),
                'guest': openapi.Schema(type=openapi.TYPE_ARRAY,
                                        description="List of users who will be guests of the interview.",
                                        items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'call_details': openapi.Schema(type=openapi.TYPE_STRING, description="Details related to the call."),
                'guest_type': openapi.Schema(type=openapi.TYPE_STRING,
                                             description="Which type of guest is the person."),
                'tech_stack': openapi.Schema(type=openapi.TYPE_STRING,
                                             description="What is the tech stack required in the interview."),
                'coding_info': openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Whether coding is required or not."),
                'status': openapi.Schema(type=openapi.TYPE_STRING,
                                         description="Status of interview."),
                'status_change': openapi.Schema(type=openapi.TYPE_STRING,
                                                description="Whether status of interview is changed or not."),

            },

            ['status']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"id": 9564, "round": 2, "status": "offer", "start_time": "2023-06-09T20:00:00Z",
                                        "end_time": "2023-06-09T21:00:00Z", "submission_id": 75609,
                                        "screening_type": "interview", "interview_mode": "voice_call", "client": "TCS",
                                        "project": None, "job_title": "Data Engineer",
                                        "supervisor_name": "Bharat Bhate", "company_name": "Innova Solutions",
                                        "marketer_name": "Consultadd Admin", "consultant_name": "Ankur Pathania"},
                               "booking_response": "Interview or Status Updated", "message": "Interview updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def destroy_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success'},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def interview_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'screening_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the submission."
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Status of the interview."
                ),
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback of the interview."
                ),
                'passed_reason': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_STRING
                    ),
                    description="List of reasons."
                )
            },

            ['status']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"id": 9472, "round": 1, "status": "offer", "start_time": "2023-05-22T15:00:37Z",
                                        "end_time": "2023-05-22T16:00:37Z", "submission_id": 74020,
                                        "screening_type": "interview", "interview_mode": "video_call",
                                        "client": "Bimodal", "project": None, "job_title": "Python Developer",
                                        "supervisor_name": "Swetha Pillai", "company_name": "BiModal Recruiting ",
                                        "marketer_name": "Vishal Choudhary", "consultant_name": "Ayushi Nigam"},
                               "booking_response": "Interview Status Updated", "message": "Interview updated"}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not found', 'response': {"message": "Interview not found"}}
        }
    )(view_func)

    return decorated_view


def interview_reschedule(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'screening_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of the submission."
                ),
                'submission': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of the submission."
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Any additional description will be put here."
                ),
                'start_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Updated start time of the interview."
                ),
                'end_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Updated end time of the interview."
                ),
                'call_details': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Any call details present."
                )
            },

            ['description', 'call_details']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {
                      "data": {"id": 9472, "round": 1, "status": "rescheduled", "start_time": "2023-05-22T15:00:37Z",
                               "end_time": "2023-05-22T16:00:37Z", "submission_id": 74020,
                               "screening_type": "interview", "interview_mode": "video_call", "client": "Bimodal",
                               "project": None, "job_title": "Python Developer", "supervisor_name": "Swetha Pillai",
                               "company_name": "BiModal Recruiting ", "marketer_name": "Vishal Choudhary",
                               "consultant_name": "Ayushi Nigam"}, "calendar": "booked",
                      "message": "Interview updated"}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not found', 'response': {"message": "This is not your Interview"}}
        }
    )(view_func)

    return decorated_view


def interview_cancel(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback of interview"
                )
            },
            []
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Interview cancelled"}},
            400: {'description': 'Bad Request'},
            404: {'description': 'No Access'}
        }
    )(view_func)

    return decorated_view


def interview_fields(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": ["feedback", "end_time", "notes", "description", "start_time", "call_details",
                         "attachment_link", "interview_mode", "screening_type", "failure_reason", "supervisor",
                         "guest"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def interview_update_notes(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'notes': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Notes of interview"
                )
            },
            ['notes']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"id": 9472, "created": "2023-05-02T13:48:19.008499Z",
                                        "modified": "2023-09-08T14:12:40.121948Z", "round": 1,
                                        "feedback": "New Feedback : \nGood\n \n New Feedback : \nGood",
                                        "guest_remark": None, "coding_present": None,
                                        "end_time": "2023-05-22T16:00:37Z", "notes": "Questions from tree were asked.",
                                        "coding_info": "coding info", "description": "Additional Info",
                                        "guest_type": "coder", "start_time": "2023-05-22T15:00:37Z",
                                        "call_details": "Calling Details", "tech_stack": "Python,AWS,Full Stack",
                                        "attachment_link": None, "screening_type": "interview",
                                        "interview_mode": "video_call", "status": "rescheduled",
                                        "if_previous_calendar": False, "failure_reason": None,
                                        "passed_reason": ["call_went_well", "coding_cleared"], "supervisor": 423,
                                        "submission": 74020, "guest": []}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def interview_put_upload_recording(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'obj_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of object it is."
                ),
                'obj_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the object."
                ),
                'file_name': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="file to upload."
                ),
                'attachment_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of attachment."
                )

            },
            ['file_name']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"data": {"url": "https://log1dev.s3..com/", "fields": {
                      "key": "media/attachments/recordings/9472/3bbadb3e-d446-4b4a-95f2-75945d9fbc3a.png",
                      "x-amz-algorithm": "AWS4-HMAC-SHA256",
                      "x-amz-credential": "AKIAUST3UQC6HCPL5TUD/20230908/ap-south-1/s3/aws4_request",
                      "x-amz-date": "20230908T141552Z", "policy": "policy",
                      "x-amz-signature": "eb5ef965f8a6643235e1b73097d8a4196b8e36b100d3a5bd1784082136c76dd7"}},
                               "message": "Recording uploaded"}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)

    return decorated_view


def interview_delete_upload_recording(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success'},
            400: {'description': 'Bad Request'}
        },
        methods=['delete']
    )(view_func)

    return decorated_view


def interview_recording(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": "url"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def interview_suggestions(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'sub_id',
                'description': "ID of submission",
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
            {
                'name': 'ctb',
                'description': "ID of supervisor",
                'type': openapi.TYPE_INTEGER
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"submission": 79240, "round": 1, "feedback": None, "screening_type": "ip_screening",
                 "status": "feedback_due", "start_time": "2023-08-03T10:24:26Z", "end_time": "2023-08-03T10:27:26Z",
                 "interview_mode": "voice_call", "client": "AKASA", "supervisor_name": "Anuj patidar",
                 "company_name": "Best High Tech", "marketer_name": "Consultadd Admin",
                 "consultant_name": "Nisha Karki"}], "total": 10033}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def interview_repeat(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'submission_id',
                'description': "ID of submission",
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"submission": 75623, "feedback": None, "screening_type": "interview", "status": "feedback_due",
                 "start_time": "2023-06-09T20:00:00Z", "end_time": "2023-06-09T21:00:00Z",
                 "interview_mode": "voice_call", "client": "", "location": "Baltimore,MD",
                 "supervisor_name": "Bharat Bhate", "company_name": "Vision Technology",
                 "marketer_name": "Priyam Kumar Singh", "consultant_name": "Aakash Sethi"}], "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def interview_assign_guest(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'guests': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="ID of coders",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                ),

            },
            []
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"data": "Coders assigned", "booking_response": 'booked'}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS},
            404: {'description': 'Not Found', 'response': {"message": "Interview not found"}}
        }
    )(view_func)

    return decorated_view


def interview_guest_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'coding_present': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Coding was present in the interview."
                ),
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback of the coder."
                ),
                'feedback_form': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback form of the coder."
                )
            },
            ['coding_present', 'feedback', 'feedback_form']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Coding Feedback Submitted"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def interview_feedback_questions(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": ["Coding Language?", "How many questions were there ?",
                                                                  "Were you able to solve the questions ?"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def interview_post_supervisor_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'feedback_form': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback form of the supervisor."
                )
            },
            ['feedback_form']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Feedback submitted"}},
            400: {'description': 'Bad Request'}
        },
        methods=['post']
    )(view_func)

    return decorated_view


def interview_put_supervisor_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'form_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of form"),
                'feedback_form': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback form of the supervisor."
                )
            },
            ['feedback_form']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Feedback updated"}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)

    return decorated_view


def interview_reasons(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "passed_reasons": [["call_went_well", "Call went well"], ["coding_cleared", "Coding cleared"],
                                   ["supervisor_was_well_prepared", "Supervisor was well prepared"],
                                   ["interviewers_were_easy_to_handle", "Interviewers were easy to handle"],
                                   ["proper_notes_were_provided_by_the_marketer",
                                    "Proper notes were provided by the marketer"]],
                "failure_reasons": [["resume_error", "Error In Resume"], ["internal_hiring", "Internal Hiring"],
                                    ["system_updated", "System Auto Update"],
                                    ["caught_mimicking", "Caught us Mimicking"],
                                    ["insufficient_skills", "Insufficient Skills"],
                                    ["test_failed", "Test Failed during Interview"],
                                    ["feedback_not_received", "Never Received Feedback"],
                                    ["irresponsible_behaviour", "Candidate's Irresponsible Behaviour"],
                                    ["lack_of_coordination", "Lack of Coordination Between Coder and Interviewee"],
                                    ["call_attempted_by_inexperienced",
                                     "Call Attempted by Someone with Less Experience"],
                                    ["client_decided_to_fill_the_role_on_a_full-time_basis",
                                     "Client Decided to Fill the Role on a Full-Time Basis"],
                                    ["hired_else", "Hired Someone Else"]]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_list(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'This parameter is used to filter the list by test id, client company name, etc.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'sort_by',
                'description': 'This parameter is used to sort the list according to created date, modified date, or by deadline.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_for',
                'description': 'This parameter is used to filter the list according to submissions made by me, my team, or all.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_json',
                'description': 'This parameter is a JSON which will filter the list by status, client, platform, marketer, vendor, deadline, and consultant.',
                'type': openapi.TYPE_OBJECT,
            },
            {
                'name': 'export',
                'description': 'This parameter is a boolean parameter which is used to check whether the user wants to export the list or not.',
                'type': openapi.TYPE_BOOLEAN
            },
            {
                'name': 'filter_by_status',
                'description': 'This parameter is used to filter the list by status.',
                'type': openapi.TYPE_STRING
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "counts": {"total": 2180, "new": 4, "failed": 456, "passed": 1342, "assigned": 2, "cancelled": 197,
                           "feedback_due": 179}, "data": [
                    {"id": 2180, "status": "feedback_due", "deadline": "2023-05-17", "company_name": "TEKsystems",
                     "submission_id": 75348, "marketer_name": "Jayesh Telang", "marketer_id": 477, "client": "Finra",
                     "consultant_name": "Chintan Modi", "submitted_by": "Sandeep Makwana",
                     "job_title": "Python developer", "skills": ["SQL", "Python"],
                     "created": "2023-05-16T18:21:35.774430Z", "modified": "2023-05-17T06:24:32.774945Z",
                     "assigned_to": [{"id": 524, "employee_name": "Utkarsh Gupta"}],
                     "engineer_associated": [{"id": 524, "employee_name": "Utkarsh Gupta"}],
                     "link": "https://online.ikmnet.com/salogin.jsp?id=b7146f376d7f816c55e1eecafc060a69t  ",
                     "additional_details": "Assessment: \tMICROSOFT SQL SERVER 2016/2017 PROGRAMMING\r\nNo. of questions: \t39\r\nMaximum Time Limit: \t98 Minutes\r\nEstimated\r\nCompletion Time: \t46 Minutes",
                     "platform": "Ikm"}], "url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_test(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the submission."
                ),
                'is_video': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Video required while giving the test."
                ),
                'is_offline': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Is the test offline."
                ),
                'con_informed': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Consultant is informed or not."
                ),
                'link': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Link of the test."
                ),
                'deadline': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Deadline of the test."
                ),
                'skills': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Skills required for the test."
                ),
                'con_zone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Consultant's timezone."
                ),
                'additional_details': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Additional details required for the test."
                ),
                'platform': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The platform on which the test will happen."
                ),
                'files': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Files required for the test."
                )
            },
            ['submission', 'skills']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "data": {"id": 2309, "status": "new", "deadline": "2023-09-19", "is_offline": False, "feedback": None,
                         "link": "abc.com", "additional_details": "additional info", "submit_date": None,
                         "engineer_remarks": None, "is_video": True, "skills": ["Python", "Java", "Nodejs"],
                         "engineers": None, "submitted_by": None, "created": "2023-09-11T06:33:40.445307Z",
                         "attachments": [{"id": 137670, "object_id": 2309, "attachment_type": "test",
                                          "file_name": "1658907125804.png",
                                          "type": {"name": "test", "display_name": "Test Docs"}}],
                         "cancel_reason": None, "assigned_to": []}, "mail": "18a82f22950f6aad",
                "message": "Test created and mail sent"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_test(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="ID of the submission."
                ),
                'is_video': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Video required while giving the test."
                ),
                'is_offline': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Is the test offline."
                ),
                'con_informed': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Consultant is informed or not."
                ),
                'link': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Link of the test."
                ),
                'deadline': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Deadline of the test."
                ),
                'skills': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Skills required for the test."
                ),
                'con_zone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Consultant's timezone."
                ),
                'additional_details': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Additional details required for the test."
                ),
                'platform': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The platform on which the test will happen."
                ),
                'files': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Files required for the test."
                )
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": {"id": 2309, "created": "2023-09-11T06:33:40.445307Z",
                                                                  "modified": "2023-09-11T06:54:12.723111Z",
                                                                  "link": "abc.in", "is_video": True,
                                                                  "is_offline": False, "feedback": None,
                                                                  "deadline": "2023-09-20", "status": "new",
                                                                  "platform": "Codility", "cancel_reason": None,
                                                                  "engineer_remarks": None, "submit_date": None,
                                                                  "additional_details": "additional infos",
                                                                  "skills": ["Python", "Java", "Nodejs", "AWS"],
                                                                  "submission": 79247, "submitted_by": None,
                                                                  "engineer": [], "assign_to": []},
                                                         "message": "Test updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_fields(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": ["link", "is_video", "is_offline", "deadline", "submit_date", "additional_details", "skills",
                         "platform"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def get_test_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "result": [["new", "New"], ["passed", "Passed"], ["failed", "Failed"], ["assigned", "Assigned"],
                           ["cancelled", "Cancelled"], ["feedback_due", "Feedback Due"]]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def get_test_platform(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': ["CoderByte", "Codility", "Coderpad", "CodeSignal", "Amcat", "Glider", "FilteredAI",
                               "Kenexa", "Hackerrank  Interviewmocha", "Hirevue", "Ikm", "Mettl", "PluralSight",
                               "LeetCode", "TestDome", "Scrum.org", "testgorilla", "Hired", "triplebyte", "Mocha",
                               "coding game", "StudySection", "Codereport", "Hackerrank", "talentCentral",
                               "ondemandassessment", "Adface", "CodeScreen", "Google Form", "imocha", "yourtechscore"]},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_assign(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'assign_to': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_INTEGER
                    ),
                    description="This is the list of IDs of the engineers."
                )
            },
            ['assign_to']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 2099, "status": "assigned", "deadline": "2023-06-28", "is_offline": True,
                         "feedback": "Successfully completed and passed the test.\r\nTotal Score: 35 out of 40\r\nTime Taken: 55 min 41 sec out of 70 min\r\nPercentage: 88%",
                         "link": "https://mettl.com/", "additional_details": "It is for full stack end developer.",
                         "submit_date": "2023-03-21T03:38:09.960538Z",
                         "engineer_remarks": "The test was completed successfully.", "is_video": True,
                         "skills": ["JavaScript", "ReactJS", "Angular", "AWS"],
                         "engineers": [{"id": 453, "employee_name": "Prem Narayan Vishwakarma"},
                                       {"id": 490, "employee_name": "Sandeep Makwana"},
                                       {"id": 484, "employee_name": "Suryam Jain"}],
                         "submitted_by": {"id": 662, "employee_name": "Pulkit Hada"},
                         "created": "2023-03-17T20:30:49.552242Z", "attachments": [], "cancel_reason": None,
                         "assigned_to": [{"id": 450, "employee_name": "Aayush Sharma"},
                                         {"id": 468, "employee_name": "Abhijith Nair"}]}, "message": "Test assigned"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_submit(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'engineer': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_INTEGER
                    ),
                    description="This is the list of IDs of the engineers."
                ),
                'remarks': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Remarks of the test."
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="File required for the test."
                ),
                'ques_answers': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Feedback form of test."
                ),
            },
            ['engineer', 'remarks', 'file', 'ques_answers']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 2099, "status": "feedback_due", "deadline": "2023-06-28", "is_offline": False,
                         "feedback": " feedback", "link": "https://mettl.com/",
                         "additional_details": "It is for full stack end developer.",
                         "submit_date": "2023-09-12T06:23:57.443156Z", "engineer_remarks": "good", "is_video": True,
                         "skills": ["JavaScript", "ReactJS", "Angular", "AWS"],
                         "engineers": [{"id": 488, "employee_name": "Aaditya sohani"},
                                       {"id": 450, "employee_name": "Aayush Sharma"},
                                       {"id": 468, "employee_name": "Abhijith Nair"},
                                       {"id": 501, "employee_name": "Abhik sahu"},
                                       {"id": 453, "employee_name": "Prem Narayan Vishwakarma"},
                                       {"id": 490, "employee_name": "Sandeep Makwana"},
                                       {"id": 484, "employee_name": "Suryam Jain"}],
                         "submitted_by": {"id": 1, "employee_name": "Consultadd Admin"},
                         "created": "2023-03-17T20:30:49.552242Z", "attachments": [], "cancel_reason": None,
                         "assigned_to": [{"id": 450, "employee_name": "Aayush Sharma"},
                                         {"id": 468, "employee_name": "Abhijith Nair"}]}, "mail": "Development Server",
                "message": "Test submitted"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback of the test."
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="File required for the test."
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Status of test."
                ),
            },
            ['status']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "data": {"id": 2099, "status": " passed", "deadline": "2023-06-28", "is_offline": False,
                         "feedback": " feedback", "link": "https://mettl.com/",
                         "additional_details": "It is for full stack end developer.",
                         "submit_date": "2023-09-12T06:23:57.443156Z", "engineer_remarks": "good", "is_video": True,
                         "skills": ["JavaScript", "ReactJS", "Angular", "AWS"],
                         "engineers": [{"id": 488, "employee_name": "Aaditya sohani"},
                                       {"id": 450, "employee_name": "Aayush Sharma"},
                                       {"id": 468, "employee_name": "Abhijith Nair"},
                                       {"id": 501, "employee_name": "Abhik sahu"},
                                       {"id": 453, "employee_name": "Prem Narayan Vishwakarma"},
                                       {"id": 490, "employee_name": "Sandeep Makwana"},
                                       {"id": 484, "employee_name": "Suryam Jain"}],
                         "submitted_by": {"id": 1, "employee_name": "Consultadd Admin"},
                         "created": "2023-03-17T20:30:49.552242Z", "attachments": [], "cancel_reason": None,
                         "assigned_to": [{"id": 450, "employee_name": "Aayush Sharma"},
                                         {"id": 468, "employee_name": "Abhijith Nair"}]},
                "message": "Test feedback added"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def test_engineer_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'feedback_form': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Feedback form of test."
                ),
                'associates': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_INTEGER
                    ),
                    description="This is the list of IDs of the engineers."
                ),
                'remarks': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Remarks of the test."
                ),
            },
            ['feedback_form', 'associates']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Feedback submitted", "mail": "18a881d1eb2031f0"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_question(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'form_name',
                'description': "Name of form by which you want to filter the questions.",
                'type': openapi.TYPE_STRING,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 44, "title": "Was coding involved in call", "category": "basic", "answer_type": "yes_question",
                 "position": 3, "is_required": True, "options": [], "dependent": [
                    {"id": 45, "title": "Were we able to code", "category": "dependent", "answer_type": "boolean",
                     "position": 4, "is_required": True, "options": [], "dependent": None, "update_options": False}],
                 "update_options": False},
                {"id": 46, "title": "Note: It is mandatory to select at least one option from these fields.",
                 "category": "basic", "answer_type": "note", "position": 5, "is_required": False, "options": [],
                 "dependent": None, "update_options": False},
                {"id": 47, "title": "What went well in call", "category": "basic", "answer_type": "multi_select",
                 "position": 6, "is_required": False,
                 "options": ["Coding on time", "Proper resume", "Good Mimicking", "Complete details from Marketer",
                             "None"], "dependent": None, "update_options": False},
                {"id": 48, "title": "Issues faced during call", "category": "basic", "answer_type": "multi_select",
                 "position": 7, "is_required": False,
                 "options": ["Coding failed", "Could not able to justify resume", "Client was very picky",
                             "Technical glitches", "Insufficient Skill",
                             "Coordination issue between Supervisor & Coder", "Incomplete details from Marketer",
                             "Mimicking issue", "Call details not received on prior to the call",
                             "Improper behaviour of interviewer", "Senior level Role",
                             "JD not match with candidate profile", "Technical Issues at Consultant's end",
                             "Technical glitches at Client’s end", "Mismatched skills and Clients on Resume",
                             "Client asked to come on-site for next rounds", "Improper Resume",
                             "No-one showed up Interview", "system incompatibility for coding",
                             "Specific requirements of just SQL server", "None"], "dependent": None,
                 "update_options": True},
                {"id": 55, "title": "Is it a final round", "category": "basic", "answer_type": "yes_question",
                 "position": 8, "is_required": True, "options": [], "dependent": [
                    {"id": 56, "title": "Offer Probability", "category": "dependent", "answer_type": "slider",
                     "position": 9, "is_required": True, "options": [], "dependent": None, "update_options": False}],
                 "update_options": False},
                {"id": 57, "title": "Select type of Interview Round", "category": "basic", "answer_type": "option",
                 "position": 9, "is_required": True, "options": ["PI 1", "PI 2"], "dependent": None,
                 "update_options": False},
                {"id": 59, "title": "Select type of Interview Round", "category": "basic", "answer_type": "text",
                 "position": 10, "is_required": True, "options": ["PI 1", "PI 2"], "dependent": None,
                 "update_options": False},
                {"id": 49, "title": "Overall Call Rating", "category": "generic", "answer_type": "rate", "position": 10,
                 "is_required": True, "options": ["Bad", "Unsatisfied", "Okay", "Satisfied", "Good"], "dependent": None,
                 "update_options": False},
                {"id": 50, "title": "Remark", "category": "generic", "answer_type": "long_text", "position": 11,
                 "is_required": True, "options": [], "dependent": None, "update_options": False},
                {"id": 60, "title": "Select type of Interview Round", "category": "basic", "answer_type": "option",
                 "position": 11, "is_required": True, "options": [], "dependent": None, "update_options": False},
                {"id": 61, "title": "Select type of Interview Round", "category": "basic", "answer_type": "option",
                 "position": 12, "is_required": True, "options": ["PI 1", "PI 2"], "dependent": None,
                 "update_options": False},
                {"id": 62, "title": "Select type of Interview Round", "category": "basic", "answer_type": "option",
                 "position": 13, "is_required": True, "options": ["PI 1", "PI 2"], "dependent": None,
                 "update_options": False},
                {"id": 63, "title": "Select type of Interview Round", "category": "basic", "answer_type": "option",
                 "position": 14, "is_required": True, "options": ["PI 1", "PI 2"], "dependent": None,
                 "update_options": False}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_question(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'position': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Position of question in form"
                ),
                'form_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the form in which you want to add a question."
                ),
                'title': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Title of the question."
                ),
                'category': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Category of the question."
                ),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of question."
                ),
                'options': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Answer options of the question.",
                    items=openapi.Items(type=openapi.TYPE_STRING)
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Description of the question."
                ),
                'placeholder': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Placeholder text of the question."
                )

            },
            ['title', 'category', 'position']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Question added to form"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def question_parent(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'value',
                'description': "No of child question you want of that parent question.",
                'type': openapi.TYPE_INTEGER,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 13, "title": "Question 1", "category": "parent", "answer_type": "headline", "position": 1,
                 "is_required": False, "options": [], "child": [
                    {"id": 26, "title": "Total test cases", "category": "child", "answer_type": "integer",
                     "position": 1, "is_required": True, "options": [], "dependent": None, "update_options": False},
                    {"id": 25, "title": "Passed test cases", "category": "child", "answer_type": "integer",
                     "position": 2, "is_required": True, "options": [], "dependent": None, "update_options": False},
                    {"id": 24, "title": "Hidden test cases were present?", "category": "child",
                     "answer_type": "yes_question", "position": 3, "is_required": True, "options": [], "dependent": [
                        {"id": 23, "title": "Hidden count", "category": "child", "answer_type": "integer",
                         "position": 4, "is_required": True, "options": [], "dependent": None,
                         "update_options": False}], "update_options": False},
                    {"id": 22, "title": "Remark", "category": "child", "answer_type": "long_text", "position": 5,
                     "is_required": True, "options": [], "dependent": None, "update_options": False}],
                 "dependent": None}]}},
            400: {'description': 'Bad Request'},
            404: {"message": ERROR_MSG, "error": "Child question not found"}
        }
    )(view_func)

    return decorated_view


def list_marketing_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'filter_json',
                'description': "JSON to filter data of particular team, skill, shift etc.",
                'type': openapi.TYPE_OBJECT
            },
            {
                'name': 'query',
                'description': "To filter data having particular employee name",
                'type': openapi.TYPE_STRING
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 95, "employee_id": 2452, "employee_name": "Arpit Mehta", "assign_consultant": {"count": 6,
                                                                                                      "consultant": [
                                                                                                          {"id": 37,
                                                                                                           "consultant_name": "Purav Thakkar"},
                                                                                                          {"id": 1036,
                                                                                                           "consultant_name": "Kshitiz Bhattarai"},
                                                                                                          {"id": 875,
                                                                                                           "consultant_name": "MIHIR UMESHKUMAR PATEL"},
                                                                                                          {"id": 1091,
                                                                                                           "consultant_name": "Mishan Tulsibhai Goti"},
                                                                                                          {"id": 1070,
                                                                                                           "consultant_name": "Mohammed Abdul Moid Arif"},
                                                                                                          {"id": 1021,
                                                                                                           "consultant_name": "Hari Krishna Ayyappa Narina"}]},
                 "team": "Consultadd Canada", "is_scrum": True, "shift": "Evening Shift (5:30 PM to 2:30 AM)",
                 "technology": [], "current_offers": {"count": 13, "project": [{"id": 57000, "client": "Luxoft/Cppib"},
                                                                               {"id": 50385, "client": "Lazard"},
                                                                               {"id": 36265, "client": "Ericsson"},
                                                                               {"id": 44723, "client": "Cargil"},
                                                                               {"id": 4377, "client": "Cummins"},
                                                                               {"id": 41126, "client": "Ibm"},
                                                                               {"id": 35348, "client": "Uhg"},
                                                                               {"id": 48048, "client": "Uhg"},
                                                                               {"id": 2404, "client": "At & T"},
                                                                               {"id": 27773,
                                                                                "client": "Bank Of America"},
                                                                               {"id": 55860, "client": "Citi Bank"},
                                                                               {"id": 54992, "client": "T Rowe"},
                                                                               {"id": 48115, "client": "T Rowe"}]}}],
                "count": {"shift": [{"name": "morning",
                                     "display_name": "Morning Shift (6 AM to 3 PM)",
                                     "count": 0}, {"name": "general",
                                                   "display_name": "General Shift (10 AM to 7 PM)",
                                                   "count": 0},
                                    {"name": "evening",
                                     "display_name": "Evening Shift (5:30 PM to 2:30 AM)",
                                     "count": 1}, {"name": "afternoon",
                                                   "display_name": "Afternoon Shift (12 Noon to 9 PM)",
                                                   "count": 0}], "team": [
                    {"id": 2, "display_name": "Boto3", "count": 0},
                    {"id": 4, "display_name": "Induci", "count": 0},
                    {"id": 5, "display_name": "Ioneq", "count": 0},
                    {"id": 6, "display_name": "NetResolute", "count": 0},
                    {"id": 8, "display_name": "OC10", "count": 0},
                    {"id": 10, "display_name": "Pythonwise", "count": 0},
                    {"id": 11, "display_name": "Zioqu", "count": 0},
                    {"id": 28, "display_name": "Account Management",
                     "count": 0},
                    {"id": 41, "display_name": "Consultadd Canada",
                     "count": 1},
                    {"id": 26, "display_name": "JLA", "count": 0},
                    {"id": 59, "display_name": "Elegant", "count": 0},
                    {"id": 60, "display_name": "Elegantc", "count": 0},
                    {"id": 3, "display_name": "Elegant Team", "count": 0}],
                          "skill": [{"display_name": "Python", "count": 0},
                                    {"display_name": "Java", "count": 0},
                                    {"display_name": "Nodejs", "count": 0},
                                    {"display_name": "JavaScript", "count": 0},
                                    {"display_name": "ReactJS", "count": 0},
                                    {"display_name": "Angular", "count": 0},
                                    {"display_name": "SQL", "count": 0},
                                    {"display_name": "AWS", "count": 0},
                                    {"display_name": "DevOps", "count": 0},
                                    {"display_name": "BA", "count": 0},
                                    {"display_name": "DA", "count": 0},
                                    {"display_name": "Peoplesoft", "count": 0},
                                    {"display_name": "Workday", "count": 0},
                                    {"display_name": "Kronos", "count": 0},
                                    {"display_name": "Lawson", "count": 0},
                                    {"display_name": "Full Stack", "count": 0},
                                    {"display_name": "Salesforce", "count": 0},
                                    {"display_name": "Cyber Security",
                                     "count": 0},
                                    {"display_name": "Other", "count": 0}]},
                "total": 1}},
            400: {'description': 'Bad Request'},
            404: {"message": ERROR_MSG, "error": "Child question not found"}
        }
    )(view_func)

    return decorated_view


def retrieve_marketing_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"count": 12, "id": 7, "name": "Nzyme", "scrum_timing": None}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def create_marketing_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of team"
                ),
                'scrum_timing': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Scrum Timing of team."
                ),
            },
            ['name', 'scrum_timing']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Team added to log1"}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def update_marketing_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of team"
                ),
                'scrum_timing': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Scrum Timing of team."
                ),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Team Details Updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def marketing_team_update_shift(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'shift': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of shift"
                ),
                'employee_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="ID of employees.",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                ),
            },
            ['shift', 'employee_ids']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Shift Detail Updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def marketing_team_get_teams(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': "To filter data by team name",
                'type': openapi.TYPE_STRING
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"count": 7, "id": 28, "name": "Account Management", "scrum_timing": None,
                 "scrum_master": [{"id": 136, "employee_name": "Kamran Adil"}]}], "total": 1}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def marketing_team_compare_teams(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'team_ids',
                'description': "IDS of teams comma separated",
                'type': openapi.TYPE_STRING
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 41, "team_name": "Consultadd Canada",
                                                                   "employee": [
                                                                       {"id": 906, "employee_name": "Bollam omkarini"},
                                                                       {"id": 1017,
                                                                        "employee_name": "DEEPAK SURYAWANSHI"},
                                                                       {"id": 634,
                                                                        "employee_name": "Gowtham Korubilli"},
                                                                       {"id": 1030, "employee_name": "Krupal Umbarkar"},
                                                                       {"id": 1039, "employee_name": "Nikita Gajbhiye"},
                                                                       {"id": 621, "employee_name": "Om Singh"},
                                                                       {"id": 1034,
                                                                        "employee_name": "Pranjal Singh Gour"},
                                                                       {"id": 944, "employee_name": "Prinal Gupta"}],
                                                                   "scrum": [
                                                                       {"id": 95, "employee_name": "Arpit Mehta"}]},
                                                                  {"id": 28, "team_name": "Account Management",
                                                                   "employee": [
                                                                       {"id": 138, "employee_name": "Bharat Bhate"},
                                                                       {"id": 121, "employee_name": "Omkar Ghugare"},
                                                                       {"id": 470, "employee_name": "Shibin K. Joy"},
                                                                       {"id": 270, "employee_name": "Smriti Singh"},
                                                                       {"id": 405, "employee_name": "Srija Reddy"},
                                                                       {"id": 469, "employee_name": "Tushar Basra"}],
                                                                   "scrum": [
                                                                       {"id": 136, "employee_name": "Kamran Adil"}]}],
                                                         "total": 2}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def marketing_team_move_employee(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="IDS of employees.",
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                )
            },
            ['employee_ids']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Marketers moved successfully", "not_moved": []}},
            400: {'description': 'Bad Request'}
        },
        methods=['put']
    )(view_func)

    return decorated_view


def marketing_team_update_scrum(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of employee."
                )
            },
            ['employee_id']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Aman Yadav appointed as scrum master for OC10."}},
            400: {'description': 'Bad Request'},
            403: {'description': DONT_HAVE_ACCESS,
                  'response': {"message": "You do not have access to perform this action"}}
        },
        methods=['put']
    )(view_func)

    return decorated_view


def marketing_team_remove_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success', 'response': {"message": "Team Removed Successfully"}},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def engineer_detail_test(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'employee_id',
                'description': "Employee ID of engineer.",
                'type': openapi.TYPE_INTEGER
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "message": {"Name": "Yash Sule", "Total point": 55.07, "Total Test": 21,
                            "assigned but not part": [2056, 2050, 2093, 1949], "Total MCQ questions": 282,
                            "Online Test": 18, "Offline Test": 3, "Total Coding Questions": 34, "submitted_tests": 17,
                            "Total Assigned Tests": 21, "Total Online Test Failed": 2, "Total  Online Passed Test": 15,
                            "Total Offline Test Passed": 2, "Total Offline Test Failed": 1,
                            "assigned_id": [1908, 1923, 1933, 1938, 1944, 1949, 1969, 1991, 1995, 2001, 2027, 2050,
                                            2056, 2092, 2093, 2107, 2120, 2126, 2147, 2162, 2167],
                            "Total FeedbackDue Online Test": 1,
                            "submitted_tests_id": [1908, 1923, 1933, 1938, 1944, 1969, 1991, 1995, 2001, 2027, 2092,
                                                   2107, 2120, 2126, 2147, 2162, 2167],
                            "Total FeedbackDue Offline Test": 0}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def engineer_detail_all(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'export',
                'description': "Do you want to export csv.",
                'type': openapi.TYPE_BOOLEAN
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"2853": {"name": "Aaditya sohani", "total_points": 2, "no_of_test_given": 1},
                         "2819": {"name": "Aayush Sharma", "total_points": 2, "no_of_test_given": 1},
                         "2925": {"name": "Abhijith Nair", "total_points": 2, "no_of_test_given": 1},
                         "8084": {"name": "Abhik sahu", "total_points": 2, "no_of_test_given": 1},
                         "2914": {"name": "Prem Narayan Vishwakarma", "total_points": 92, "no_of_test_given": 46},
                         "2879": {"name": "Sandeep Makwana", "total_points": 114, "no_of_test_given": 57},
                         "2874": {"name": "Suryam Jain", "total_points": 84, "no_of_test_given": 42},
                         "2943": {"name": "Harsh Singhal", "total_points": 48, "no_of_test_given": 24},
                         "2849": {"name": "Nitin Dwivedi", "total_points": 48, "no_of_test_given": 24},
                         "2927": {"name": "Prakhar Patidar", "total_points": 42, "no_of_test_given": 21},
                         "2797": {"name": "Dipraj Panwar", "total_points": 58, "no_of_test_given": 29},
                         "2976": {"name": "Gaurav Rawat", "total_points": 30, "no_of_test_given": 15},
                         "10019": {"name": "Sahil Kharche", "total_points": 80, "no_of_test_given": 40},
                         "2851": {"name": "Mudit tiwari", "total_points": 18, "no_of_test_given": 9},
                         "2854": {"name": "Piyush Joshi", "total_points": 10, "no_of_test_given": 5},
                         "2909": {"name": "Prerna Chitransh", "total_points": 72, "no_of_test_given": 36},
                         "2876": {"name": "Utkarsh Gupta", "total_points": 48, "no_of_test_given": 24},
                         "2667": {"name": "Aman Kumar Singh", "total_points": 2, "no_of_test_given": 1},
                         "2728": {"name": "Vijay Patidar", "total_points": 8, "no_of_test_given": 4},
                         "2895": {"name": "Niraj Kumar Lathar", "total_points": 92, "no_of_test_given": 46},
                         "2903": {"name": "Rajendra chourasiya", "total_points": 30, "no_of_test_given": 15},
                         "2946": {"name": "Rishabh Raghuwanshi", "total_points": 52, "no_of_test_given": 26},
                         "2944": {"name": "Sourabh Patidar", "total_points": 6, "no_of_test_given": 3},
                         "2875": {"name": "Abhishek Bhandari", "total_points": 66, "no_of_test_given": 33},
                         "2929": {"name": "Ayush Raj Keshri", "total_points": 46, "no_of_test_given": 23},
                         "2890": {"name": "Gaurav Verma", "total_points": 54, "no_of_test_given": 27},
                         "2727": {"name": "Ayush Bendwal", "total_points": 12, "no_of_test_given": 6},
                         "2724": {"name": "Gyanendra Singh Chandrawat", "total_points": 24, "no_of_test_given": 12},
                         "3087": {"name": "Sahil Namdeo", "total_points": 6, "no_of_test_given": 3},
                         "2922": {"name": "Rutvik Kapade", "total_points": 70, "no_of_test_given": 35},
                         "2881": {"name": "Shruti Itoria", "total_points": 40, "no_of_test_given": 20},
                         "2864": {"name": "Jayesh rathore", "total_points": 72, "no_of_test_given": 36},
                         "10005": {"name": "Yash Sule", "total_points": 34, "no_of_test_given": 17},
                         "2930": {"name": "Akash Katuri", "total_points": 54, "no_of_test_given": 27},
                         "2907": {"name": "Darshan hirekurubar", "total_points": 76, "no_of_test_given": 38},
                         "2884": {"name": "Harsh mishra", "total_points": 72, "no_of_test_given": 36},
                         "2761": {"name": "Priyam Kumar Singh", "total_points": 2, "no_of_test_given": 1},
                         "3098": {"name": "Khushi Shrivastava", "total_points": 8, "no_of_test_given": 4},
                         "3095": {"name": "Rashi Jaiswal", "total_points": 10, "no_of_test_given": 5},
                         "10009": {"name": "Chinmay Raiker", "total_points": 2, "no_of_test_given": 1},
                         "2731": {"name": "Mandeep Lamba", "total_points": 6, "no_of_test_given": 3},
                         "3086": {"name": "Aarti Bhawsar", "total_points": 12, "no_of_test_given": 6},
                         "3082": {"name": "Mansi Jaiswal", "total_points": 10, "no_of_test_given": 5},
                         "10004": {"name": "Yash Thakur", "total_points": 12, "no_of_test_given": 6},
                         "2924": {"name": "Aman Singh", "total_points": 6, "no_of_test_given": 3},
                         "2915": {"name": "Anuj patidar", "total_points": 2, "no_of_test_given": 1},
                         "2857": {"name": "Akshay saxena", "total_points": 2, "no_of_test_given": 1},
                         "2877": {"name": "Adarsh kumar singh", "total_points": 8, "no_of_test_given": 4},
                         "2923": {"name": "Anish kumar nirala", "total_points": 8, "no_of_test_given": 4},
                         "2848": {"name": "Brijendra Kumar Yadav", "total_points": 4, "no_of_test_given": 2},
                         "2865": {"name": "Manmohan sharma", "total_points": 4, "no_of_test_given": 2},
                         "2846": {"name": "Vansh Verma", "total_points": 2, "no_of_test_given": 1},
                         "2932": {"name": "Priyanka Prajapat", "total_points": 14, "no_of_test_given": 7},
                         "2618": {"name": "Nishchay Zinzore", "total_points": 2, "no_of_test_given": 1},
                         "2627": {"name": "Prashant Kumar", "total_points": 2, "no_of_test_given": 1},
                         "10015": {"name": "Dev Sahu", "total_points": 6, "no_of_test_given": 3},
                         "2637": {"name": "Snehal Dinkar Barge", "total_points": 2, "no_of_test_given": 1},
                         "2732": {"name": "Mayank Singhal", "total_points": 2, "no_of_test_given": 1}}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view
