from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS
from utils_app.utils import generate_swagger_auto_schema


def list_payroll(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {'results': [
                {'id': 24, 'pay_date': '2021-12-31', 'pay_day': 'Friday', 'processing_date': '2021-12-29',
                 'pay_period_end': '2021-12-15', 'pay_period_start': '2021-11-16'},
                {'id': 25, 'pay_date': '2022-01-31', 'pay_day': 'Monday', 'processing_date': '2022-01-27',
                 'pay_period_end': '2022-01-15', 'pay_period_start': '2021-12-16'}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_timesheet(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {'result': [
                {'id': 267, 'client': 'Athena Health (Timesheets)    ', 'start_date': None, 'employer': 'consultadd',
                 'status': 'terminated-fired_performance_issue', 'total_hours': '0hrs', 'work_type': 'C2C',
                 'timesheet_frequency': None},
                {'id': 138, 'client': 'Berklee College Of Music (Timesheets)    ', 'start_date': None,
                 'employer': 'Nzyme', 'status': 'terminated-fired_performance_issue', 'total_hours': '0hrs',
                 'work_type': 'C2C', 'timesheet_frequency': None},
                {'id': 1336, 'client': 'T Rowe Price (Timesheets)', 'start_date': '2023-05-15', 'employer': 'Induci',
                 'status': 'joined', 'total_hours': '0hrs', 'work_type': 'C2C', 'timesheet_frequency': None}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def retrieve_timesheet(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {'result': [
                {'id': 37974, 'start': '05/15/2023', 'end': '05/21/2023', 'status': 'draft', 'hours': 0.0,
                 'additional_hours': 0.0, 'submitted_at': None, 'status_updated_at': None, 'status_updated_by': None,
                 'modified': '2023-05-17T15:37:34.301304Z', 'remark': None,
                 'project': {'id': 1283, 'employer': 'Pythonwise', 'start_date': '2023-02-15',
                             'vendor': 'Revolent Group', 'project_type': 'W2(Contract)', 'timesheet_frequency': None,
                             'client': 'Cognizant (PayStubs)'}, 'con_comment': None},
                {'id': 37975, 'start': '05/22/2023', 'end': '05/28/2023', 'status': 'draft', 'hours': 0.0,
                 'additional_hours': 0.0, 'submitted_at': None, 'status_updated_at': None, 'status_updated_by': None,
                 'modified': '2023-05-17T15:37:56.849076Z', 'remark': None,
                 'project': {'id': 1283, 'employer': 'Pythonwise', 'start_date': '2023-02-15',
                             'vendor': 'Revolent Group', 'project_type': 'W2(Contract)', 'timesheet_frequency': None,
                             'client': 'Cognizant (PayStubs)'}, 'con_comment': None}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def timesheet_frequency(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {'result': {'timesheet': True, 'project_type': 'w2', 'timesheet_frequency': None}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def timesheet_set_frequency(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'frequency': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Frequency of timesheet.'
                )
            },
            ['frequency']
        ],
        responses={
            201: {'description': 'Success', 'response': {'message': 'Timesheet frequency updated successfully'}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_timesheet(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'attachments': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Previous attachments of timesheet.'
                ),
                'zero_hours': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Do you want to set timesheet hours to zero.'
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Hours of timesheet.'
                ),
                'comment': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Consultant comment of timesheet.'
                ),
                'file1': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='First attachment of timesheet.'
                ),
                'file2': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Second attachment of timesheet.'
                ),
            },
            ['hours', 'file1']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                'result': {'id': 38181, 'start': '01/16/2023', 'end': '01/22/2023', 'status': 'submitted', 'hours': 40,
                           'additional_hours': 16, 'submitted_at': '2023-09-13T07:51:17.020663Z',
                           'status_updated_at': None, 'status_updated_by': None,
                           'modified': '2023-09-13T07:51:17.020684Z', 'remark': None,
                           'project': {'id': 911, 'employer': 'NetResolute', 'start_date': '2021-11-01',
                                       'vendor': 'Luxoft', 'project_type': 'C2C', 'timesheet_frequency': 'Weekly',
                                       'client': 'Cpp Investment (TimeSheets)'},
                           'con_comment': 'timesheet of september'}, 'timesheet_id': 38181}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def timesheet_history(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {'result': [
                {'id': 19700, 'start': '11/01/2021', 'end': '11/06/2021', 'status': 'approved', 'hours': 40,
                 'additional_hours': 0, 'submitted_at': '2021-11-09T01:30:11.422389Z',
                 'status_updated_at': '2021-11-10T15:33:58.213943Z', 'status_updated_by': 325,
                 'modified': '2021-11-10T15:33:58.213973Z', 'remark': '',
                 'project': {'id': 911, 'employer': 'NetResolute', 'start_date': '2021-11-01', 'vendor': 'Luxoft',
                             'project_type': 'C2C', 'timesheet_frequency': 'Weekly',
                             'client': 'Cpp Investment (TimeSheets)'}, 'con_comment': ''}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def timesheet_contact_us(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'message': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Message to send.'
                ),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Contact department of company.'
                ),
                'device_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of device from where you are sending mail.'
                )
            },
            ['type']
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": "mail sent"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def timesheet_cancel(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 38186, "start": "05/29/2023", "end": "06/04/2023", "status": "draft", "hours": 0.0,
                           "additional_hours": 0.0, "submitted_at": None, "status_updated_at": None,
                           "status_updated_by": None, "modified": "2023-09-13T08:10:51.273032Z", "remark": None,
                           "project": {"id": 1283, "employer": "Pythonwise", "start_date": "2023-02-15",
                                       "vendor": "Revolent Group", "project_type": "W2(Contract)",
                                       "timesheet_frequency": "Weekly", "client": "Cognizant (PayStubs)"},
                           "con_comment": None}}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not Found', 'response': {"error": "Timesheet not found"}}
        }
    )(view_func)

    return decorated_view


def timesheet_attachments(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"result": [
                {"id": 130922, "file_path": "url", "extension": "csv", "created": "2023-09-13T07:53:50.749696Z",
                 "file_name": "CurrentEmployeeList.csv"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def timesheet_request(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'start_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Start date of timesheet.'
                ),
                'end_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='End date of timesheet.'
                ),
            },
            ['start', 'end']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "TimeSheet request sent"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def consultant_leave_balance(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"result": [
                {"id": 10280, "granted": 0.0, "balance": 0.0, "leave_type": "Covid emergency sick leave", "year": 2022,
                 "is_expired": False},
                {"id": 10279, "granted": 0.0, "balance": 0.0, "leave_type": "Marriage leave", "year": 2022,
                 "is_expired": False},
                {"id": 10278, "granted": 0.0, "balance": 0.0, "leave_type": "Paternity", "year": 2022,
                 "is_expired": False},
                {"id": 10277, "granted": 0.0, "balance": 0.0, "leave_type": "Maternity", "year": 2022,
                 "is_expired": False},
                {"id": 10276, "granted": 0.0, "balance": 0.0, "leave_type": "PTO", "year": 2022, "is_expired": False},
                {"id": 10275, "granted": 0.0, "balance": 0.0, "leave_type": "Sick leave", "year": 2022,
                 "is_expired": False}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def consultant_leave_apply(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'leave_type': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of leave type of consultant.'
                ),
                'to_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='End date of leave.'
                ),
                'from_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Start date of leave.'
                ),
                'duration_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Duration type of leave.'
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='No of hours of leave required.'
                ),
                'attachment': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Attachment of leave.'
                ),
            },
            ['leave_type', 'to_date', 'from_date', 'duration_type']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "leave applied successfully"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def consultant_leave_history(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"result": [
                {"id": 61, "leave_type": "PTO", "to_date": "2022-10-24", "from_date": "2022-10-24", "total_hours": 8,
                 "applied_on": "2022-11-21", "status": "approved", "description": "Diwali", "attachment": [
                    {"id": 109859, "file_path": "url", "extension": "jpeg", "created": "2022-11-21T17:57:59.043364Z",
                     "file_name": "IMG_5834.jpeg"}], "duration_type": "Full"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def consultant_leave_type(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"result": [{"id": 9688, "leave_type": "PTO", "balance": 68.0},
                                                                    {"id": 9690, "leave_type": "Paternity",
                                                                     "balance": 64.0},
                                                                    {"id": 9691, "leave_type": "Maternity",
                                                                     "balance": 72.0},
                                                                    {"id": 9687, "leave_type": "Sick leave",
                                                                     "balance": 8.0},
                                                                    {"id": 9692, "leave_type": "Marriage leave",
                                                                     "balance": 0.0}, {"id": 9689,
                                                                                       "leave_type": "Covid emergency sick leave",
                                                                                       "balance": 40.0}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def consultant_leave_holiday(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "result": ["01/02/2023", "01/16/2023", "02/20/2023", "05/29/2023", "06/19/2023", "07/04/2023",
                           "09/04/2023", "10/09/2023", "11/13/2023", "11/23/2023", "11/24/2023", "12/25/2023"]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_event(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"result": [
                {"action_link": None, "event_type": "External", "id": 6, "start": "2023-08-01", "is_active": False,
                 "end": "2023-09-01", "consultant_id": 1, "title": "Title", "description": "Description",
                 "image": "https://log1dev.s3.ap-south-1.amazonaws.com/media/"}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def event_feedback(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Feedback of event.'
                ),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Event Feedback Submitted"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def retrieve_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 1327, "status": "joined",
                                                                  "submission": {"id": 72694, "lead": {"id": 70471,
                                                                                                       "job_desc": "Job description.",
                                                                                                       "job_title": "Python Developer",
                                                                                                       "primary_skill": None,
                                                                                                       "city": "Work from home,US",
                                                                                                       "vendor_company_id": 4121,
                                                                                                       "vendor_company_name": "Empire Staffing Group",
                                                                                                       "owner": "Abhishek Jha",
                                                                                                       "status": "sub",
                                                                                                       "created": "2023-04-06T18:36:56.830226Z",
                                                                                                       "modified": "2023-04-06T18:36:57.012376Z",
                                                                                                       "is_w2": False,
                                                                                                       "position_name": "Python Developer",
                                                                                                       "position_type": "C2C"},
                                                                                 "rate": 75, "client": "Columbia U",
                                                                                 "employer": "Consultadd",
                                                                                 "email": "ankur87pathania@gmail.com",
                                                                                 "phone": "18622349320",
                                                                                 "status": "project",
                                                                                 "is_active": False,
                                                                                 "vendor_contact": None,
                                                                                 "date_of_birth": "1990-09-02",
                                                                                 "visa_type": "gc",
                                                                                 "visa_start": "2022-09-01",
                                                                                 "visa_end": "2024-08-31",
                                                                                 "education": "Doctor of Business Administration ",
                                                                                 "linkedin": "http://www.linkedin.com/in/ankurpathania2990/",
                                                                                 "other_link": "http://www.linkedin.com/in/ankurpathania2990/",
                                                                                 "current_city": "California",
                                                                                 "attachments": [], "interviews": [
                                                                          {"id": 9365, "guest": [
                                                                              {"id": 522, "employee_id": 2898,
                                                                               "email": "amarnadh.s@consultadd.com",
                                                                               "employee_name": "Amarnadh sabbisetti",
                                                                               "team": "Briskers(Python)",
                                                                               "roles": ["engineer"], "gender": "male",
                                                                               "phone": "7675947909",
                                                                               "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/8107.png",
                                                                               "is_superuser": False,
                                                                               "technology": ["Python", "SQL"]},
                                                                              {"id": 600, "employee_id": 2848,
                                                                               "email": "brijendra.y@consultadd.com",
                                                                               "employee_name": "Brijendra Kumar Yadav",
                                                                               "team": "Artizens(MEAN)",
                                                                               "roles": ["engineer"], "gender": "male",
                                                                               "phone": "918738904913",
                                                                               "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/2848.png",
                                                                               "is_superuser": False,
                                                                               "technology": ["JavaScript"]},
                                                                              {"id": 408, "employee_id": 2779,
                                                                               "email": "jeetram.y@consultadd.com",
                                                                               "employee_name": "Jeetram Yadav",
                                                                               "team": "Emeralds(Python)",
                                                                               "roles": ["engineer"], "gender": "male",
                                                                               "phone": "1234567890",
                                                                               "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/2779.png",
                                                                               "is_superuser": False,
                                                                               "technology": None}],
                                                                           "supervisor": {"id": 295,
                                                                                          "employee_id": 2671,
                                                                                          "email": "ankush.s@consultadd.com",
                                                                                          "employee_name": "Ankush Sharma",
                                                                                          "team": "Training",
                                                                                          "roles": ["interviewee",
                                                                                                    "trainer",
                                                                                                    "scrum_master"],
                                                                                          "gender": "male",
                                                                                          "phone": "91",
                                                                                          "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/2671.png",
                                                                                          "is_superuser": False,
                                                                                          "technology": None},
                                                                           "attachment_link": None,
                                                                           "created": "2023-04-07T16:09:49.452101Z",
                                                                           "modified": "2023-04-10T21:08:55.077193Z",
                                                                           "round": 1,
                                                                           "feedback": "New Feedback : \nThey want to proceed to a Final round which is a code challenge.",
                                                                           "guest_remark": "It was introductory call with few technical questions on Django. Call went well.",
                                                                           "coding_present": False,
                                                                           "end_time": "2023-04-10T15:30:20Z",
                                                                           "notes": None, "coding_info": "",
                                                                           "description": "", "guest_type": "assigned",
                                                                           "start_time": "2023-04-10T15:00:20Z",
                                                                           "call_details": "https://www.google.com/url?q=https%3A%2F%2Fmeetings.ringcentral.com%2Fj%2F5741715109&sa=D&source=calendar&usd=2&usg=AOvVaw10jg1NQGsaEiWJUwfzkQ3V",
                                                                           "tech_stack": "Python,Django,AWS",
                                                                           "screening_type": "interview",
                                                                           "interview_mode": "video_call",
                                                                           "status": "next_round",
                                                                           "if_previous_calendar": False,
                                                                           "failure_reason": None,
                                                                           "passed_reason": ["call_went_well",
                                                                                             "supervisor_was_well_prepared",
                                                                                             "interviewers_were_easy_to_handle"],
                                                                           "submission": 72694}, {"id": 9375, "guest": [
                                                                              {"id": 492, "employee_id": 2877,
                                                                               "email": "Adarsh.k.Singh@consultadd.com",
                                                                               "employee_name": "Adarsh kumar singh",
                                                                               "team": "Product Team",
                                                                               "roles": ["engineer"], "gender": "male",
                                                                               "phone": "9981956460",
                                                                               "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/8075.png",
                                                                               "is_superuser": False,
                                                                               "technology": ["Python", "Nodejs",
                                                                                              "JavaScript", "ReactJS"]},
                                                                              {"id": 481, "employee_id": 2923,
                                                                               "email": "anish.k@consultadd.com",
                                                                               "employee_name": "Anish kumar nirala",
                                                                               "team": "Decoder", "roles": ["engineer"],
                                                                               "gender": "male",
                                                                               "phone": "918651363083", "avatar": None,
                                                                               "is_superuser": False,
                                                                               "technology": ["Python", "SQL",
                                                                                              "JavaScript", "Other"]}],
                                                                                                  "supervisor": {
                                                                                                      "id": 427,
                                                                                                      "employee_id": 2805,
                                                                                                      "email": "vishwajeet.t@consultadd.com",
                                                                                                      "employee_name": "Vishwajeet Thakur",
                                                                                                      "team": "Briskers(Python)",
                                                                                                      "roles": [
                                                                                                          "engineer",
                                                                                                          "interviewee"],
                                                                                                      "gender": "male",
                                                                                                      "phone": "918119877435",
                                                                                                      "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/2805.png",
                                                                                                      "is_superuser": False,
                                                                                                      "technology": [
                                                                                                          "Python",
                                                                                                          "SQL", "AWS",
                                                                                                          "Terraform"]},
                                                                                                  "attachment_link": None,
                                                                                                  "created": "2023-04-10T21:10:46.302167Z",
                                                                                                  "modified": "2023-04-17T20:46:42.789845Z",
                                                                                                  "round": 2,
                                                                                                  "feedback": "New Feedback : \n Give me a call when you get a chance. They want to offer you the position. Thanks",
                                                                                                  "guest_remark": "Interviewer asked us 1 python coding related to arranging list using three pointer approach and then asked us to create django data models and write some shell django query. We were able to solve all of them. Overall, it was good.",
                                                                                                  "coding_present": True,
                                                                                                  "end_time": "2023-04-13T16:30:30Z",
                                                                                                  "notes": None,
                                                                                                  "coding_info": "",
                                                                                                  "description": "",
                                                                                                  "guest_type": "assigned",
                                                                                                  "start_time": "2023-04-13T15:00:30Z",
                                                                                                  "call_details": "",
                                                                                                  "tech_stack": "Python,Django",
                                                                                                  "screening_type": "interview",
                                                                                                  "interview_mode": "video_call",
                                                                                                  "status": "offer",
                                                                                                  "if_previous_calendar": False,
                                                                                                  "failure_reason": None,
                                                                                                  "passed_reason": [
                                                                                                      "call_went_well",
                                                                                                      "supervisor_was_well_prepared",
                                                                                                      "proper_notes_were_provided_by_the_marketer"],
                                                                                                  "submission": 72694}],
                                                                                 "test": [], "project": {"id": 1327,
                                                                                                         "status": "joined",
                                                                                                         "created": "2023-04-17T21:15:18.328271Z",
                                                                                                         "duration": "12",
                                                                                                         "start_date": "2023-05-01",
                                                                                                         "end_date": "2024-05-01",
                                                                                                         "city": "Work from home,US",
                                                                                                         "feedback": None,
                                                                                                         "consultant": 201,
                                                                                                         "vendor_address": "16 Kass Rd, White Plains, NY 10605",
                                                                                                         "client_address": "Address533 W. 218th St. New York, NY 10034",
                                                                                                         "payment_term": 30,
                                                                                                         "invoicing_period": 7,
                                                                                                         "is_msg_sent": True,
                                                                                                         "check_list": {
                                                                                                             "total": 6,
                                                                                                             "msa": 0,
                                                                                                             "work_order": 0,
                                                                                                             "status": True,
                                                                                                             "msa_signed": 1,
                                                                                                             "start_date": 1,
                                                                                                             "client_address": 1,
                                                                                                             "vendor_address": 1,
                                                                                                             "work_order_signed": 1,
                                                                                                             "reporting_details": 1},
                                                                                                         "reporting_details": "Not Received Yet",
                                                                                                         "rate": 80,
                                                                                                         "employer": "Consultadd",
                                                                                                         "attachments": [
                                                                                                             {
                                                                                                                 "id": 128069,
                                                                                                                 "object_id": 1327,
                                                                                                                 "attachment_type": "work_order_msa_signed",
                                                                                                                 "file_name": "ConsultADDITSPA_1.pdf",
                                                                                                                 "type": {
                                                                                                                     "name": "work_order_msa_signed",
                                                                                                                     "display_name": "Work Order and MSA/Agreement Signed"}}],
                                                                                                         "is_remote": False,
                                                                                                         "consultant_name": "Ankur Pathania"},
                                                                                 "comments": [],
                                                                                 "marketer_name": "Abhishek Jha",
                                                                                 "marketer_id": 436,
                                                                                 "consultant": {"id": 201,
                                                                                                "last_login": None,
                                                                                                "created": "2019-10-16T18:51:20.320000Z",
                                                                                                "modified": "2023-05-01T19:05:27.212206Z",
                                                                                                "is_w2": False,
                                                                                                "is_active": True,
                                                                                                "first_login": False,
                                                                                                "remote_only": False,
                                                                                                "email": "ankur.pathania2990@gmail.com",
                                                                                                "internal_employee": False,
                                                                                                "name": "Ankur Pathania",
                                                                                                "ssn": "333595246",
                                                                                                "date_of_birth": "1990-09-02",
                                                                                                "links": "http://www.linkedin.com/in/ankurpathania2990/",
                                                                                                "domain": None,
                                                                                                "skills": "BA,Python",
                                                                                                "skype": None,
                                                                                                "country": "USA",
                                                                                                "timezone": "PDT",
                                                                                                "phone_no": "(408) 478-9065",
                                                                                                "current_city": "California",
                                                                                                "marital_status": None,
                                                                                                "gender": "male",
                                                                                                "status": "on_project",
                                                                                                "work_type": "Full Time",
                                                                                                "p_is_active": True,
                                                                                                "visa_petition": True,
                                                                                                "pin": "228778"},
                                                                                 "is_complete": True}, "feedback": None,
                                                                  "check_list": {"total": 6, "msa": 0, "work_order": 0,
                                                                                 "status": True, "msa_signed": 1,
                                                                                 "start_date": 1, "client_address": 1,
                                                                                 "vendor_address": 1,
                                                                                 "work_order_signed": 1,
                                                                                 "reporting_details": 1},
                                                                  "attachments": [{"id": 128069, "object_id": 1327,
                                                                                   "attachment_type": "work_order_msa_signed",
                                                                                   "file_name": "ConsultADDITSPA_1.pdf",
                                                                                   "type": {
                                                                                       "name": "work_order_msa_signed",
                                                                                       "display_name": "Work Order and MSA/Agreement Signed"}}],
                                                                  "created": "2023-04-17T21:15:18.328271Z",
                                                                  "city": "Work from home,US", "duration": "12",
                                                                  "invoicing_period": 7,
                                                                  "client_address": "Address533 W. 218th St. New York, NY 10034",
                                                                  "vendor_address": "16 Kass Rd, White Plains, NY 10605",
                                                                  "payment_term": 30, "start_date": "2023-05-01",
                                                                  "end_date": "2024-05-01", "rate": 80,
                                                                  "employer": "Consultadd",
                                                                  "reporting_details": "Not Received Yet",
                                                                  "is_remote": False, "marketer_name": "Abhishek Jha"},
                                                         "permission": {"update": False}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'To filter data based on query.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'sort_by',
                'description': 'To sort data based on date.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'filter_for',
                'description': 'To filter the projects based on my, team etc.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'filter_json',
                'description': 'To filter the data based on various parameters like client, work_type etc.',
                'type': openapi.TYPE_OBJECT,
            },
            {
                'name': 'export',
                'description': 'Do you want to export data or not.',
                'type': openapi.TYPE_BOOLEAN,
            },
            {
                'name': 'filter_by_time',
                'description': 'To filter data by time.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'filter_by_lead',
                'description': 'To filter data by lead.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'filter_by_status',
                'description': 'To filter data by status.',
                'type': openapi.TYPE_STRING,
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "counts": {"new": 16, "total": 1207, "joined": 306, "received": 16, "on_boarded": 12, "not_joined": 12},
                "data": [{"id": 15, "status": "joined", "feedback": None, "created": "2019-07-25T15:49:35.015000Z",
                          "duration": "12 months", "submission": 678, "start_date": "2019-08-05",
                          "client": "State Of Maine", "rate": 70, "city": "Augusta,ME", "end_date": "2021-06-01",
                          "consultant_name": "Divisha Leeladhar Rajput",
                          "check_list": {"total": 6, "msa": 1, "work_order": 1, "status": True, "msa_signed": 1,
                                         "start_date": 1, "client_address": 1, "vendor_address": 1,
                                         "work_order_signed": 1, "reporting_details": 1},
                          "marketer_name": "Nandini Goswami", "company_name": "Extrinsicerp/ Bg Staffing Inc",
                          "is_remote": None, "support": [], "employer": "Pythonwise", "work_type": "C2C"}],
                "file_url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'submission': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of submission.'
                ),
                'work_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Work type of project.'
                ),
                'is_remote': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Project is remote or not.'
                ),
                'duration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Duration of project.'
                ),
                'start_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Start date of project.'
                )
            },
            ['submission']
        ],
        responses={
            201: {'description': 'Success', 'response': {'message': 'Timesheet frequency updated successfully'}},
            400: {'description': 'Bad Request'},
            406: {'description': 'Already exists', 'response': {"message": "Project already exist"}}
        }
    )(view_func)

    return decorated_view


def update_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[

            {
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Status of project.'
                ),
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='City of project.'
                ),
                'is_remote': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Project is remote or not.'
                ),
                'duration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Duration of project.'
                ),
                'start_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Start date of project.'
                ),
                'end_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='End date of project.'
                ),
                'rate': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Rate of project.'
                ),
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Feedback of project.'
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Employer of project.'
                ),
                'payment_term': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Payment Term of project.'
                ),
                'client_address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Address of client.'
                ),
                'vendor_address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Address of vendor.'
                ),
                'invoicing_period': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Invoicing period of project.'
                ),
                'reporting_details': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Reporting details Term of project.'
                ),
                'remote_consultant_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of consultant.'
                ),
                'remote_consultant_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Consultant type of project.'
                ),
            },
            ['status']
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": {"id": 1283, "status": "terminated",
                                                                  "feedback": "Cognizant pulled out of contract with Revolent and Revolent is no more able to deploy us to them. Because of that they terminated our employment effective immediately. My whole team is fired on a call together",
                                                                  "created": "2023-02-14T20:58:14.593922Z",
                                                                  "duration": "10", "submission": 67168,
                                                                  "start_date": "2023-02-15", "client": "Cognizant",
                                                                  "rate": 75000.0, "city": "Remote,US",
                                                                  "end_date": "2023-05-15",
                                                                  "consultant_name": "Anuj patidar",
                                                                  "check_list": {"total": 5, "status": False,
                                                                                 "start_date": 1, "offer_letter": 0,
                                                                                 "client_address": 1,
                                                                                 "vendor_address": 1,
                                                                                 "reporting_details": 1},
                                                                  "marketer_name": "Kanak Pareek",
                                                                  "company_name": "Revolent Group", "is_remote": False,
                                                                  "support": [], "employer": "Pythonwise",
                                                                  "work_type": "W2(Contract)"}, "error": None,
                                                         "message": "Project updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def project_mail_to_onboard(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'project_id',
                'description': 'ID of project.',
                'type': openapi.TYPE_INTEGER,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "On-boarding mail sent", "error": "ok"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_send_support_mail(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": 'Mail sent', "message": "Support and Offer mail sent"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_fields(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": ["owner"]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_remove_remote(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"message": "Remote consultant is removed"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_project_support(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"data": [{"id": 1067, "status": {"value": "less_active", "change_date": "2023-05-01"},
                                         "support": {"id": 458, "email": "gaurav.v@consultadd.com",
                                                     "name": "Gaurav Verma"}, "created": "2023-02-24T04:12:50.504635Z",
                                         "modified": "2023-05-02T05:58:38.189643Z", "feedback": None, "end": None,
                                         "start": "2023-02-24", "is_proxy_support": False}, {"id": 1066, "status": None,
                                                                                             "support": {"id": 655,
                                                                                                         "email": "sahil.k@consultadd.com",
                                                                                                         "name": "Sahil Kharche"},
                                                                                             "created": "2023-02-24T04:12:50.496305Z",
                                                                                             "modified": "2023-04-28T03:38:25.246753Z",
                                                                                             "feedback": None,
                                                                                             "end": None,
                                                                                             "start": "2023-03-01",
                                                                                             "is_proxy_support": True}],
                               "is_project_description": True}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_project_support(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'is_proxy_support': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Support is proxy or not."
                ),
                'support': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of engineer"
                ),
                'proxy_start_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Start date of proxy support"
                ),
                'proxy_support_person': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of proxy engineer"
                ),
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Start date of support"
                ),
                'end': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="End date of support"
                ),

            },
            ['support', 'start']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": 'Support assignment mail send & Support is added'}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_project_support(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'is_proxy_support': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Support is proxy or not."
                ),
                'support': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of engineer"
                ),
                'feedback': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="feedback of support"
                ),
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Start date of support"
                ),
                'end': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="End date of support"
                ),

            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Support is updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def project_support_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="frequency of support"
                ),
                'change_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Change date of support"
                ),

            },
            ['status']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Support status is updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def project_support_initiate(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'support': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of engineer"
                ),
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Start date of support"
                ),

            },
            ['support']
        ],
        responses={
            202: {'description': 'Success',
                  'response': {"message": "Support is initiated", "result": "18a8eae3efb557c1"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def project_support_remove(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"message": "Support is removed"}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': {"message": DONT_HAVE_ACCESS}}
        }
    )(view_func)

    return decorated_view


def project_support_update_details(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'proxy_support_person': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of proxy engineer"
                ),
                'proxy_start_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Start date of proxy support"
                ),
                'support': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of support engineer"
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Status of support"
                ),
                'change_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Change date of support"
                ),
            },
            ['support', 'proxy_support_person', 'status', 'change_date']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Support detail is updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_project_order(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'project_id',
                'description': 'ID of project.',
                'type': openapi.TYPE_INTEGER,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 218,
                                                                   "created_by": {"id": 438, "employee_id": 2912,
                                                                                  "email": "anish.a@consultadd.com",
                                                                                  "employee_name": "Anish Alam",
                                                                                  "team": "Induci",
                                                                                  "roles": ["marketer"],
                                                                                  "gender": "male",
                                                                                  "phone": "917370034914",
                                                                                  "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/8053.png",
                                                                                  "is_superuser": False,
                                                                                  "technology": None}, "attachments": [
                    {"id": 130353, "object_id": 1340, "attachment_type": "work_order_msa_signed",
                     "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                     "type": {"name": "work_order_msa_signed", "display_name": "Work Order and MSA/Agreement Signed"}},
                    {"id": 129931, "object_id": 1340, "attachment_type": "work_order_signed",
                     "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                     "type": {"name": "work_order_signed", "display_name": "Work Order Signed"}}],
                                                                   "created": "2023-05-16T13:57:37.943037Z",
                                                                   "modified": "2023-05-16T13:57:37.943040Z",
                                                                   "field": "rate", "value": "70",
                                                                   "effective_date": "2023-05-10", "project": 1340}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_project_order(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'project_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of project.'
                ),
                'effective_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Effective end of project.'
                ),
                'field': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Field to be added in description.'
                ),
                'value': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Value of field.'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Attachment of project order.'
                )
            },
            ['project_id']
        ],
        responses={
            201: {'description': 'Success', 'response': {"data": [{"id": 225,
                                                                   "created_by": {"id": 1, "employee_id": 1000,
                                                                                  "email": "product@consultadd.com",
                                                                                  "employee_name": "Consultadd Admin",
                                                                                  "team": "Product Team",
                                                                                  "roles": ["superadmin", "marketer",
                                                                                            "engineer", "legal"],
                                                                                  "gender": "male",
                                                                                  "phone": "1234567890",
                                                                                  "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/1000.png",
                                                                                  "is_superuser": True,
                                                                                  "technology": ["Angular"]},
                                                                   "attachments": [{"id": 130353, "object_id": 1340,
                                                                                    "attachment_type": "work_order_msa_signed",
                                                                                    "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                    "type": {
                                                                                        "name": "work_order_msa_signed",
                                                                                        "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                   {"id": 129931, "object_id": 1340,
                                                                                    "attachment_type": "work_order_signed",
                                                                                    "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                    "type": {
                                                                                        "name": "work_order_signed",
                                                                                        "display_name": "Work Order Signed"}}],
                                                                   "created": "2023-09-13T13:37:37.608874Z",
                                                                   "modified": "2023-09-13T13:37:37.608876Z",
                                                                   "field": None, "value": None, "effective_date": None,
                                                                   "project": 1340}, {"id": 224, "created_by": None,
                                                                                      "attachments": [{"id": 130353,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_msa_signed",
                                                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_msa_signed",
                                                                                                           "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                                      {"id": 129931,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_signed",
                                                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_signed",
                                                                                                           "display_name": "Work Order Signed"}}],
                                                                                      "created": "2023-09-13T13:37:36.028334Z",
                                                                                      "modified": "2023-09-13T13:37:36.028337Z",
                                                                                      "field": None, "value": None,
                                                                                      "effective_date": None,
                                                                                      "project": 1340},
                                                                  {"id": 223, "created_by": None, "attachments": [
                                                                      {"id": 130353, "object_id": 1340,
                                                                       "attachment_type": "work_order_msa_signed",
                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                       "type": {"name": "work_order_msa_signed",
                                                                                "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                      {"id": 129931, "object_id": 1340,
                                                                       "attachment_type": "work_order_signed",
                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                       "type": {"name": "work_order_signed",
                                                                                "display_name": "Work Order Signed"}}],
                                                                   "created": "2023-09-13T13:37:09.259456Z",
                                                                   "modified": "2023-09-13T13:37:09.259462Z",
                                                                   "field": None, "value": None, "effective_date": None,
                                                                   "project": 1340}, {"id": 222, "created_by": None,
                                                                                      "attachments": [{"id": 130353,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_msa_signed",
                                                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_msa_signed",
                                                                                                           "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                                      {"id": 129931,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_signed",
                                                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_signed",
                                                                                                           "display_name": "Work Order Signed"}}],
                                                                                      "created": "2023-09-13T13:36:20.475972Z",
                                                                                      "modified": "2023-09-13T13:36:20.475977Z",
                                                                                      "field": None, "value": None,
                                                                                      "effective_date": None,
                                                                                      "project": 1340},
                                                                  {"id": 221, "created_by": None, "attachments": [
                                                                      {"id": 130353, "object_id": 1340,
                                                                       "attachment_type": "work_order_msa_signed",
                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                       "type": {"name": "work_order_msa_signed",
                                                                                "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                      {"id": 129931, "object_id": 1340,
                                                                       "attachment_type": "work_order_signed",
                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                       "type": {"name": "work_order_signed",
                                                                                "display_name": "Work Order Signed"}}],
                                                                   "created": "2023-09-13T13:35:03.515084Z",
                                                                   "modified": "2023-09-13T13:35:03.515092Z",
                                                                   "field": None, "value": None, "effective_date": None,
                                                                   "project": 1340}, {"id": 220, "created_by": None,
                                                                                      "attachments": [{"id": 130353,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_msa_signed",
                                                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_msa_signed",
                                                                                                           "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                                      {"id": 129931,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_signed",
                                                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_signed",
                                                                                                           "display_name": "Work Order Signed"}}],
                                                                                      "created": "2023-09-13T13:35:02.842523Z",
                                                                                      "modified": "2023-09-13T13:35:02.842531Z",
                                                                                      "field": None, "value": None,
                                                                                      "effective_date": None,
                                                                                      "project": 1340},
                                                                  {"id": 219, "created_by": None, "attachments": [
                                                                      {"id": 130353, "object_id": 1340,
                                                                       "attachment_type": "work_order_msa_signed",
                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                       "type": {"name": "work_order_msa_signed",
                                                                                "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                      {"id": 129931, "object_id": 1340,
                                                                       "attachment_type": "work_order_signed",
                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                       "type": {"name": "work_order_signed",
                                                                                "display_name": "Work Order Signed"}}],
                                                                   "created": "2023-09-13T13:35:02.236034Z",
                                                                   "modified": "2023-09-13T13:35:02.236037Z",
                                                                   "field": None, "value": None, "effective_date": None,
                                                                   "project": 1340}, {"id": 218,
                                                                                      "created_by": {"id": 438,
                                                                                                     "employee_id": 2912,
                                                                                                     "email": "anish.a@consultadd.com",
                                                                                                     "employee_name": "Anish Alam",
                                                                                                     "team": "Induci",
                                                                                                     "roles": [
                                                                                                         "marketer"],
                                                                                                     "gender": "male",
                                                                                                     "phone": "917370034914",
                                                                                                     "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/8053.png",
                                                                                                     "is_superuser": False,
                                                                                                     "technology": None},
                                                                                      "attachments": [{"id": 130353,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_msa_signed",
                                                                                                       "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_msa_signed",
                                                                                                           "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                                      {"id": 129931,
                                                                                                       "object_id": 1340,
                                                                                                       "attachment_type": "work_order_signed",
                                                                                                       "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                                       "type": {
                                                                                                           "name": "work_order_signed",
                                                                                                           "display_name": "Work Order Signed"}}],
                                                                                      "created": "2023-05-16T13:57:37.943037Z",
                                                                                      "modified": "2023-05-16T13:57:37.943040Z",
                                                                                      "field": "rate", "value": "70",
                                                                                      "effective_date": "2023-05-10",
                                                                                      "project": 1340}],
                                                         "message": "Project order created"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def update_project_order(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'effective_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Effective end of project.'
                ),
                'field': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Field to be added in description.'
                ),
                'value': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Value of field.'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Attachment of project order.'
                )
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"data": {"id": 225,
                                                                  "created_by": {"id": 1, "employee_id": 1000,
                                                                                 "email": "product@consultadd.com",
                                                                                 "employee_name": "Consultadd Admin",
                                                                                 "team": "Product Team",
                                                                                 "roles": ["superadmin", "marketer",
                                                                                           "engineer", "legal"],
                                                                                 "gender": "male",
                                                                                 "phone": "1234567890",
                                                                                 "avatar": "https://log1dev.s3.ap-south-1.amazonaws.com/media/avatar/1000.png",
                                                                                 "is_superuser": True,
                                                                                 "technology": ["Angular"]},
                                                                  "attachments": [{"id": 130353, "object_id": 1340,
                                                                                   "attachment_type": "work_order_msa_signed",
                                                                                   "file_name": "fc2ccdbe-8772-44f6-905f-435e5d68b596.pdf",
                                                                                   "type": {
                                                                                       "name": "work_order_msa_signed",
                                                                                       "display_name": "Work Order and MSA/Agreement Signed"}},
                                                                                  {"id": 129931, "object_id": 1340,
                                                                                   "attachment_type": "work_order_signed",
                                                                                   "file_name": "iVedha_Offer_of_Employment___Jatin_Patel_1.pdf",
                                                                                   "type": {"name": "work_order_signed",
                                                                                            "display_name": "Work Order Signed"}}],
                                                                  "created": "2023-09-13T13:37:37.608874Z",
                                                                  "modified": "2023-09-13T13:45:03.059399Z",
                                                                  "field": None, "value": None, "effective_date": None,
                                                                  "project": 1340},
                                                         "message": "Project order updated"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_eng_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'End date of project.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Start date of project.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 1340, "consultant__name": "Vishal Rathod", "consultant__email": "vishal.r@consultadd.com",
                 "feedback": None, "start_date": "2023-05-10", "consultant__phone_no": None,
                 "created": "2023-05-10T13:48:31.950278Z", "modified": "2023-09-13T13:37:37.610872Z",
                 "end_date": "2024-05-10", "employer": "Induci", "location": "Remote,US", "status": "new",
                 "client": "Cnb", "job_desc": "Job Description", "job_title": "ELK-DevOps",
                 "marketer_email": "anish.a@consultadd.com", "vendor": "iVedha Inc", "marketer_name": "Anish Alam",
                 "relation": None, "recruiter": None}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_rate_revision(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'End date of rate revision.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Start date of rate revision.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'query',
                'description': 'To filter data by consultant name.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'margin',
                'description': 'Margin of rate revision.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'export',
                'description': 'To export data in csv.',
                'type': openapi.TYPE_BOOLEAN,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"rate": 70, "po_rate": 75, "last_revision": "2023-03-09", "consultant_id": 999,
                 "consultant_name": "KHUSHBOO BANSAL", "consultant_email": "Khushboo.bansal92@gmail.com",
                 "marketer_name": "Bessie Josina Heloise", "marketer_email": "josina.h@consultadd.com",
                 "margin": "5.0(6.67%)", "vendor_name": "Turnberry"}], "url": None, "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
