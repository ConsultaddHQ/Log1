from drf_yasg import openapi

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
