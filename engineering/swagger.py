from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS
from utils_app.utils import generate_swagger_auto_schema


def list_engineering(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'employee or consultant name', 'type': openapi.TYPE_STRING},
            {'name': 'filter_json', 'description': "Filter data based on various parameters like support, client etc",
             'type': openapi.TYPE_STRING},
            {'name': 'filter_for', 'description': "Filter for 'my' or 'team' or 'all'", 'type': openapi.TYPE_STRING},
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 1336,
                                                                   "consultant": {"id": 1035, "name": "Samyak Jain",
                                                                                  "email": "samyakjain3028@gmail.com",
                                                                                  "location": "Lawrence, Kansas"},
                                                                   "support": [{"email": "Darshan.h@consultadd.com",
                                                                                "name": "Darshan hirekurubar"}],
                                                                   "start_date": "2023-05-15",
                                                                   "submission": {"location": "Work from home,US",
                                                                                  "job_title": "Python Engineer",
                                                                                  "client": "T. Rowe Price",
                                                                                  "vendor": "Vision Technology"},
                                                                   "project_status": "Joined",
                                                                   "support_status": "active", "remark": None,
                                                                   "assignment_status": "Assigned",
                                                                   "support_required": True,
                                                                   "is_project_description": True}], "total": 1,
                                                         "counts": {"support_status": {
                                                             "training": {"display_name": "Training", "count": 0},
                                                             "active": {"display_name": "Active", "count": 1},
                                                             "less_active": {"display_name": "Less Active", "count": 0},
                                                             "independent": {"display_name": "Independent", "count": 0},
                                                             "handover": {"display_name": "Handover", "count": 0},
                                                             "terminated": {"display_name": "Terminated", "count": 0}},
                                                             "project_status": {
                                                                 "new": {"display_name": "New", "count": 0},
                                                                 "received": {"display_name": "Received",
                                                                              "count": 0},
                                                                 "on_boarded": {"display_name": "On Boarded",
                                                                                "count": 0},
                                                                 "joined": {"display_name": "Joined",
                                                                            "count": 1},
                                                                 "complete": {"display_name": "Complete",
                                                                              "count": 0},
                                                                 "cancelled": {"display_name": "Cancelled",
                                                                               "count": 0},
                                                                 "terminated": {"display_name": "Terminated",
                                                                                "count": 0}},
                                                             "assignment_count": {
                                                                 "all": {"display_name": "All", "count": 1261},
                                                                 "assigned": {"display_name": "Assigned",
                                                                              "count": 1},
                                                                 "unassigned": {"display_name": "Unassigned",
                                                                                "count": 0},
                                                                 "old_projects": {"display_name": "Old Projects",
                                                                                  "count": 0},
                                                                 "support_not_required": {
                                                                     "display_name": "Support Not Required",
                                                                     "count": 0}}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def retrieve_engineering(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 1202, "consultant": {"id": 61,
                                                                                             "recruiter": {"id": 49,
                                                                                                           "employee_name": "Nupur Pandit",
                                                                                                           "email": "nupur.p@consultadd.com"},
                                                                                             "retention": {"id": 67,
                                                                                                           "employee_name": "Rajeev Ranjan",
                                                                                                           "email": "rajeev.r@consultadd.com"},
                                                                                             "name": "Bharat Bhate",
                                                                                             "email": "bhatebharat@gmail.com",
                                                                                             "location": "New York,NY"},
                                                                  "start_date": "2021-10-25", "submission": {
                    "resume": {"id": 104889, "name": "attachments/marketing_submission/60581/SampleResume.pdf"},
                    "location": "Remote,US", "job_title": "ELK Developer", "client": "Availity",
                    "vendor": "Placeholder-Remote Vendor"}, "remote_consultant": {"id": 698,
                                                                                  "name": "Shrikant Upadhyay",
                                                                                  "email": "shrikant.u@consultadd.com"},
                                                                  "marketer": {"id": 1,
                                                                               "email": "product@consultadd.com",
                                                                               "name": "Consultadd Admin"},
                                                                  "is_remote": True, "support_required": True}}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not Found', 'response': {"message": "Project not found"}}
        }
    )(view_func)

    return decorated_view


def engineering_filters(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {
                "project_status": [{"name": "new", "display_name": "New"},
                                   {"name": "received", "display_name": "Received"},
                                   {"name": "on_boarded", "display_name": "On Boarded"},
                                   {"name": "joined", "display_name": "Joined"},
                                   {"name": "complete", "display_name": "Complete"},
                                   {"name": "cancelled", "display_name": "Cancelled"},
                                   {"name": "terminated", "display_name": "Terminated"}],
                "support_status": [{"name": "training", "display_name": "Training"},
                                   {"name": "active", "display_name": "Active"},
                                   {"name": "less_active", "display_name": "Less Active"},
                                   {"name": "independent", "display_name": "Independent"},
                                   {"name": "handover", "display_name": "Handover"},
                                   {"name": "terminated", "display_name": "Terminated"}],
                "assignment_status": [{"name": "all", "display_name": "All"},
                                      {"name": "assigned", "display_name": "Assigned"},
                                      {"name": "unassigned", "display_name": "Unassigned"},
                                      {"name": "old_projects", "display_name": "Old Projects"},
                                      {"name": "support_not_required", "display_name": "Support Not Required"}]}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def engineering_activity(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 70158, "user": {"id": 609, "employee_id": 2927,
                                                                                         "email": "prakhar.p@consultadd.com",
                                                                                         "employee_name": "Prakhar Patidar",
                                                                                         "team": "Awesome",
                                                                                         "roles": ["engineer"],
                                                                                         "gender": "male",
                                                                                         "phone": "919755333422",
                                                                                         "avatar": None,
                                                                                         "is_superuser": False,
                                                                                         "technology": ["Python",
                                                                                                        "AWS"]},
                                                                   "activity_type": "created",
                                                                   "desc": "Prakhar Patidar updated the project description",
                                                                   "object_id": 1307,
                                                                   "created": "2023-03-15T07:31:17.842104Z",
                                                                   "content_type": 74}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def engineering_timesheet(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'start', 'description': 'Start date of timesheet', 'type': openapi.TYPE_STRING},
            {'name': 'end', 'description': "End date of timesheet",
             'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 36491, "start": "03/27/2023", "end": "04/02/2023", "status": "approved", "hours": 40,
                 "additional_hours": 0, "submitted_at": "2023-04-03T20:38:07.926793Z",
                 "status_updated_at": "2023-04-05T14:28:44.990123Z", "status_updated_by": 973,
                 "modified": "2023-04-05T14:28:44.990153Z", "attachments": [
                    {"id": 125780, "file_name": "2023_nikhilmatlani_1.jpeg", "attachment_type": "timesheet",
                     "type": {"name": "timesheet", "display_name": "Timesheet"}}], "remark": "", "con_comment": ""}],
                "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def engineering_guidelines(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"first_day": "first day", "guideline": "guideline"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def engineering_support_required(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'support_required': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Support required or not'),
            },
            ['support_required']
        ],
        responses={
            202: {'description': 'Success', 'response': {'message': 'project support marked as required'}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_project_updates(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 1004, "blocker": "", "update_by": {"id": 495,
                                                                                                            "email": "Jayesh.r@consultadd.com",
                                                                                                            "name": "Jayesh rathore"},
                                                                   "tagged_user": [], "attachments": [],
                                                                   "created": "2023-05-05T08:08:08.285186Z",
                                                                   "modified": "2023-05-05T08:08:08.285189Z",
                                                                   "end": None, "start": "2023-05-04",
                                                                   "update": "<p>Started Python Training</p>",
                                                                   "blocker_solution": None, "blocker_resolved": None,
                                                                   "type": "project"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def retrieve_project_updates(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 1081, "blocker": "React package dependency",
                                                                  "update_by": {"id": 1,
                                                                                "email": "product@consultadd.com",
                                                                                "name": "Consultadd Admin"},
                                                                  "tagged_user": [
                                                                      {"id": 1, "email": "product@consultadd.com",
                                                                       "name": "Consultadd Admin"},
                                                                      {"id": 1000, "email": "khushi.s@consultadd.com",
                                                                       "name": "Khushi Shrivastava"}], "attachments": [
                    {"id": 130908, "file_name": "", "attachment_type": "project_update",
                     "type": {"name": "project_update", "display_name": "Project Update"}}],
                                                                  "created": "2023-08-07T07:54:59.997004Z",
                                                                  "modified": "2023-08-15T06:47:33.337419Z",
                                                                  "end": "2023-07-31", "start": "2023-06-26",
                                                                  "update": "It is 90% complete.",
                                                                  "blocker_solution": "Found react package",
                                                                  "blocker_resolved": True, "type": "project"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_project_updates(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'update': {
                    'type': openapi.TYPE_STRING,
                    'description': 'Update of project.'
                },
                'blocker': {
                    'type': openapi.TYPE_STRING,
                    'description': 'What is the blocker (if any).'
                },
                'blocker_resolved': {
                    'type': openapi.TYPE_BOOLEAN,
                    'description': 'Blocker resolved or not.'
                },
                'blocker_solution': {
                    'type': openapi.TYPE_STRING,
                    'description': 'Solution of blocker.'
                },
                'start': {
                    'type': openapi.TYPE_STRING,
                    'format': 'date',
                    'description': 'Start date of sprint.'
                },
                'end': {
                    'type': openapi.TYPE_STRING,
                    'format': 'date',
                    'description': 'End date of sprint.'
                },
                'type': {
                    'type': openapi.TYPE_STRING,
                    'description': 'Type of update (Project/Training).'
                },
                'tagged_user': {
                    'type': openapi.TYPE_INTEGER,
                    'description': 'ID of user if tagged.'
                },
                'files': {
                    'type': openapi.TYPE_ARRAY,
                    'description': 'Files of that update.',
                    'items': {
                        'type': openapi.TYPE_STRING
                    }
                }
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Project Update is added successfully"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_project_updates(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'update': openapi.Schema(type=openapi.TYPE_STRING, description='Update of project.'),
                'blocker': openapi.Schema(type=openapi.TYPE_STRING, description='What is the blocker (if any).'),
                'blocker_resolved': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Blocker resolved or not.'),
                'blocker_solution': openapi.Schema(type=openapi.TYPE_STRING, description='Solution of blocker.'),
                'start': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Start date of sprint.'),
                'end': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='End date of sprint.'),
                'type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of update (Project/Training).'),
                'tagged_user': {
                    'type': openapi.TYPE_INTEGER,
                    'description': 'ID of user if tagged.'
                },
                'files': {
                    'type': openapi.TYPE_ARRAY,
                    'description': 'Files of that update.',
                    'items': {
                        'type': openapi.TYPE_STRING
                    }
                }
            }
            ,
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Project update is edited successfully"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_updates_blocker(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'blocker_resolved': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                   description='Blocker is resolved or not.'),
                'blocker_solution': openapi.Schema(type=openapi.TYPE_STRING,
                                                   description='What is the solution of blocker.')
            }
            ,
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Project update edited successfully"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_updates_add_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='Document to upload.')
            }
            ,
            ['file']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Document is uploaded"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_updates_remove_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'attachment_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of document')
            }
            ,
            ['attachment_id']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Document removed"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_project_summary(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"resume": {"id": 129459, "name": "Brett_Bhate_-_Silverlane_ELK_Stack_Consultant_1.docx"},
                         "recordings": [],
                         "description": {"id": 1499, "notes": None, "remark": None, "resource": None, "timezone": None,
                                         "technology": None, "description": None, "daily_support_hour": None,
                                         "consultant_preferred_time": None}, "job_description": "Job description",
                         "recruiter": None, "retention": None,
                         "marketer": {"id": 180, "email": "arun.k@consultadd.com", "name": "Arun Kumar"}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_project_summary(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'notes': openapi.Schema(type=openapi.TYPE_STRING, description='Notes for the project.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remarks of project.'),
                'resource': openapi.Schema(type=openapi.TYPE_STRING, description='Resources to complete the project.'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of project.'),
                'timezone': openapi.Schema(type=openapi.TYPE_STRING, description='Timezone to complete project.'),
                'technology': openapi.Schema(type=openapi.TYPE_STRING, description='Technology of project.'),
                'daily_support_hour': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                     description='Number of daily support hours given to consultant.'),
                'consultant_preferred_time': openapi.Schema(type=openapi.TYPE_STRING,
                                                            description="Consultant's preferred time to work.")
            }, [],
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Project description created",
                                                         "data": {"id": 1501, "created": "2023-05-10T13:48:32.020148Z",
                                                                  "modified": "2023-08-15T08:21:01.385706Z",
                                                                  "notes": "Need to have good django knowledge",
                                                                  "remark": "We should able to complete project by this week",
                                                                  "resource": "javatpoint.com",
                                                                  "description": "A requirement of python backend developer",
                                                                  "timezone": "EST", "technology": "Python",
                                                                  "daily_support_hour": "8",
                                                                  "consultant_preferred_time": "EST", "update_by": None,
                                                                  "project": 1340}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_project_summary(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'notes': openapi.Schema(type=openapi.TYPE_STRING, description='Notes for the project.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remarks of project.'),
                'resource': openapi.Schema(type=openapi.TYPE_STRING, description='Resources to complete the project.'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of project.'),
                'timezone': openapi.Schema(type=openapi.TYPE_STRING, description='Timezone to complete project.'),
                'technology': openapi.Schema(type=openapi.TYPE_STRING, description='Technology of project.'),
                'daily_support_hour': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                     description='Number of daily support hours given to consultant.'),
                'consultant_preferred_time': openapi.Schema(type=openapi.TYPE_STRING,
                                                            description="Consultant's preferred time to work.")
            }, [],
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Project description updated",
                                                         "data": {"id": 1501, "created": "2023-05-10T13:48:32.020148Z",
                                                                  "modified": "2023-08-15T08:23:37.189943Z",
                                                                  "notes": "Need to have good django knowledge + Angular",
                                                                  "remark": "We should able to complete project by this month",
                                                                  "resource": "w3schools.com",
                                                                  "description": "A requirement of python full stack developer",
                                                                  "timezone": "EST", "technology": "Python",
                                                                  "daily_support_hour": "8",
                                                                  "consultant_preferred_time": "EST", "update_by": None,
                                                                  "project": 1340}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def project_summary_technology(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": ["Python", "Java", "Nodejs", "JavaScript", "ReactJS", "Angular", "SQL", "AWS", "DevOps", "BA",
                         "DA", "Peoplesoft", "Workday", "Kronos", "Lawson", "Full Stack", "Salesforce",
                         "Cyber Security"]}}
        }
    )(view_func)

    return decorated_view


def project_summary_get_resource(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": {"id": 1501, "resource": "w3schools.com"}}},
            400: {'description': 'Bad Request'},
            404: {'description': 'Not Found', 'response': {"message": "Project not found"}}
        },
        methods=['get']
    )(view_func)

    return decorated_view


def project_summary_put_resource(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'resource': openapi.Schema(type=openapi.TYPE_STRING, description='Resource of project')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Project description updated"}},
            400: {'description': 'Bad Request', },
        },
        methods=['put']
    )(view_func)

    return decorated_view


def project_summary_get_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 130909, "file_name": "Consultadd.png", "attachment_type": "project_resource",
                 "type": {"name": "project_resource", "display_name": "Project Resource"}}]}},
            400: {'description': 'Bad Request', },
        },
        methods=['get']
    )(view_func)

    return decorated_view


def project_summary_put_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file': openapi.Schema(type=openapi.TYPE_FILE, description='File to upload')
            },
            ['file']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Resource Uploaded"}},
            400: {'description': 'Bad Request', },
        },
        methods=['put']
    )(view_func)

    return decorated_view


def project_summary_delete_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'attachment_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of attachment')
            },
            ['attachment_id']
        ],
        responses={
            204: {'description': 'Success', 'response': {"message": "Attachment deleted"}},
            400: {'description': 'Bad Request', },
        },
        methods=['delete']
    )(view_func)

    return decorated_view


def list_project_training(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 338, "created": "2023-08-07T11:01:08.008152Z", "modified": "2023-08-07T11:01:08.008159Z",
                 "position": 1, "remark": "Remark of training agenda", "duration": "Duration of project",
                 "description": None, "assignment_given": True, "status": None, "completion_date": None,
                 "assignment_submitted": None, "project": 1340, "created_by": 1}]}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def create_project_training(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of agenda.'),
                'duration': openapi.Schema(type=openapi.TYPE_STRING, description='Duration of agenda.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remark of training agenda.'),
                'assignment_given': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                   description='Whether assignment is given or not.'),
                'assignment_submitted': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                       description='Assignment submitted or not.')
            },
            []
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Agenda added"}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def update_project_training(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of agenda.'),
                'duration': openapi.Schema(type=openapi.TYPE_STRING, description='Duration of agenda.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remark of training agenda.'),
                'assignment_given': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                   description='Whether assignment is given or not.'),
                'assignment_submitted': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                       description='Assignment submitted or not.'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Status of agenda.'),
                'completion_date': openapi.Schema(type=openapi.TYPE_STRING, description='Completion date of agenda.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Agenda updated"}},
            400: {'description': 'Bad Request', },
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def delete_project_training(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of agenda.'),
                'duration': openapi.Schema(type=openapi.TYPE_STRING, description='Duration of agenda.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remark of training agenda.'),
                'assignment_given': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                   description='Whether assignment is given or not.'),
                'assignment_submitted': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                       description='Assignment submitted or not.'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Status of agenda.'),
                'completion_date': openapi.Schema(type=openapi.TYPE_STRING, description='Completion date of agenda.')
            },
            []
        ],
        responses={
            204: {'description': 'Success', 'response': {"message": "Agenda Deleted"}},
            400: {'description': 'Bad Request', },
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        }
    )(view_func)

    return decorated_view


def list_project_checklist(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 3003, "created": "2023-05-10T13:48:32.030092Z", "modified": "2023-08-07T11:36:20.993943Z",
                 "position": 7, "task": "Resume Preparation (for client side)", "remark": "Checklist completed",
                 "status": "complete", "project": 1340}]}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def update_project_checklist(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Status of checklist.'),
                'remark': openapi.Schema(type=openapi.TYPE_STRING, description='Remark of checklist.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Agenda Deleted"}},
            400: {'description': 'Bad Request', }
        }
    )(view_func)

    return decorated_view


def list_engineer_report(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'category', 'description': 'To filter data based on different categories',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query', 'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'To filter data based on project status', 'type': openapi.TYPE_STRING},
            {'name': 'remote', 'description': 'Project is remote or not', 'type': openapi.TYPE_STRING},
            {'name': 'export', 'description': 'Export list in CSV or not', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 85, "employee_id": 2369, "email": "adarsh.k@consultadd.com", "employee_name": "Adarsh Kumar",
                 "project": {"bandwidth": 1, "data": [
                     {"id": 161, "created": "2020-08-13T17:26:34.912687Z", "start": "2020-08-03", "end": None,
                      "feedback": None, "support_status": "active",
                      "consultant": {"id": 890, "name": "Adarsh kumar singh", "email": "Adarsh.k.Singh@consultadd.com",
                                     "contact": None},
                      "project": {"id": 508, "status": "Joined", "end_date": "2021-08-03", "feedback": "",
                                  "is_remote": True, "start_date": "2020-08-03", "client": "TrueBlue"},
                      "description": {"remarks": None, "technology": "Sr. Cloud Engineer", "timezone": "EDT"},
                      "support_info": {"duration": 36.3, "start": "2020-08-03"}, "modified_at": None}]}}], "counts": {
                "support_status": {"active": {"display_name": "Active", "count": 52},
                                   "training": {"display_name": "Training", "count": 0},
                                   "less_active": {"display_name": "Less Active", "count": 6},
                                   "independent": {"display_name": "Independent", "count": 27},
                                   "handover": {"display_name": "Handover", "count": 27},
                                   "terminated": {"display_name": "Terminated", "count": 27},
                                   "total": {"display_name": "Total", "count": 58}}}, "url": "", "total": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_remote_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'category', 'description': 'To filter data based on different categories.',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query.', 'type': openapi.TYPE_STRING},
            {'name': 'project_status', 'description': 'To filter data based on project status.',
             'type': openapi.TYPE_STRING},
            {'name': 'export', 'description': 'Export list in CSV or not.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"url": "", "counts": {
                "project_status": {"active": {"display_name": "Active", "count": 0},
                                   "training": {"display_name": "Training", "count": 1},
                                   "closed": {"display_name": "Closed", "count": 1},
                                   "total": {"display_name": "Total", "count": 2}}}, "data": [
                {"id": 1118, "consultant": {"id": 61, "name": "Bharat Bhate", "remote_employee": "Sanidhya Goyal"},
                 "support_info": {"name": "Support not Required", "start_date": "", "status": "independent",
                                  "duration": 14.0}, "start_date": "2022-06-20",
                 "project_detail": {"client": "Abra", "timezone": "PST", "technology": "Java", "status": "Training",
                                    "remarks": None}}], "total": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_project(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'category', 'description': 'To filter data based on different categories.',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query.', 'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'To filter data based on project status.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 161, "created": "2020-08-13T17:26:34.912687Z", "start": "2020-08-03", "end": None,
                 "feedback": None, "support_status": "active",
                 "consultant": {"id": 890, "name": "Adarsh kumar singh", "email": "Adarsh.k.Singh@consultadd.com",
                                "contact": None},
                 "project": {"id": 508, "status": "Joined", "end_date": "2021-08-03", "feedback": "", "is_remote": True,
                             "start_date": "2020-08-03", "client": "TrueBlue"},
                 "description": {"remarks": None, "technology": "Sr. Cloud Engineer", "timezone": "EDT"},
                 "support_info": {"duration": 36.3, "start": "2020-08-03"}, "modified_at": None}], "count": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_test(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'category', 'description': 'To filter data based on different categories.',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query.', 'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'To filter data based on project status.', 'type': openapi.TYPE_STRING},
            {'name': 'start', 'description': 'Minimum created date of test.', 'type': openapi.TYPE_STRING},
            {'name': 'end', 'description': 'Maximum created date of test.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 2189, "status": "feedback_due", "deadline": "2023-06-28",
                 "skills": ["JavaScript", "ReactJS", "Angular", "AWS"],
                 "consultant": {"id": 201, "name": "Ankur Pathania", "email": "ankur.pathania2990@gmail.com"},
                 "submission": {"id": 75609, "client": "TCS", "job_title": "Data Engineer",
                                "marketer_name": "Consultadd Admin", "vendor_company": "Innova Solutions"}}],
                "count": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_interview(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'catagory', 'description': 'To filter data based on different categories.',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query.', 'type': openapi.TYPE_STRING},
            {'name': 'type', 'description': 'To filter data based on guest type.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 9560, "status": "feedback_due", "round": 1,
                                                                   "consultant": {"id": 1108,
                                                                                  "name": "Vijayasimhan Ganesan",
                                                                                  "email": "vijayasimhan0397@gmail.com"},
                                                                   "start_time": "2023-05-19T11:30:20Z",
                                                                   "supervisor": "Manish Mali",
                                                                   "submission": {"id": 74811, "client": "SIG",
                                                                                  "job_title": "Software developer",
                                                                                  "marketer_name": "Alka Pachori",
                                                                                  "vendor_company": "CSS Tec"}}],
                                                         "count": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_terminated(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'category', 'description': 'To filter data based on different categories.',
             'type': openapi.TYPE_STRING},
            {'name': 'query', 'description': 'To filter data based on some query.', 'type': openapi.TYPE_STRING},
            {'name': 'status', 'description': 'To filter data based on status of project.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 792, "created": "2022-06-06T07:48:03.182965Z", "start": "2022-06-07", "end": "2022-10-19",
                 "feedback": None, "support_status": "handover",
                 "consultant": {"id": 541, "name": "Savan Kared", "email": "savan.kared93@gmail.com",
                                "contact": "(909) 358-5899"},
                 "project": {"id": 1114, "status": "Project Terminated", "end_date": "2022-10-10",
                             "feedback": "feedback",
                             "is_remote": False, "start_date": "2022-07-11", "client": "Capital Group"},
                 "description": {"remarks": None, "technology": "Python", "timezone": "PST"},
                 "support_info": {"duration": 3.1, "start": "2022-06-23"},
                 "modified_at": {"id": 484, "date": "2022-10-10"}}], "count": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def engineer_report_category(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"name": "client", "display_name": "Client Name"},
                                                                  {"name": "vendor_name",
                                                                   "display_name": "Vendor Name"},
                                                                  {"name": "support_name",
                                                                   "display_name": "Support Name"},
                                                                  {"name": "consultant_name",
                                                                   "display_name": "Consultant Name"}]}}
        }
    )(view_func)

    return decorated_view


def engineer_report_summary(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'filter_by', 'description': 'To filter data based on date.', 'type': openapi.TYPE_STRING},
            {'name': 'start', 'description': 'Start date of summary.', 'type': openapi.TYPE_STRING},
            {'name': 'end', 'description': 'End date of summary.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": {"test": {"total": 89, "status_counts": [
                {"name": "New", "count": 0}, {"name": "Passed", "count": 59}, {"name": "Failed", "count": 23},
                {"name": "Assigned", "count": 0}, {"name": "Cancelled", "count": 0},
                {"name": "Feedback_due", "count": 7}]}, "project": {"total": 27,
                                                                    "status_counts": [{"name": "Active", "count": 0},
                                                                                      {"name": "Terminated",
                                                                                       "count": 15},
                                                                                      {"name": "Less Active",
                                                                                       "count": 0},
                                                                                      {"name": "Independent",
                                                                                       "count": 12}]},
                                                                  "technology": {"total": 16, "status_counts": [
                                                                      {"name": "Python", "count": 2},
                                                                      {"name": None, "count": 11},
                                                                      {"name": "AWS", "count": 2},
                                                                      {"name": "Java", "count": 1}]},
                                                                  "guest_interview": {"total": 3, "status_counts": [
                                                                      {"name": "Offer", "count": 0},
                                                                      {"name": "Failed", "count": 2},
                                                                      {"name": "Cancelled", "count": 0},
                                                                      {"name": "Next Round", "count": 1},
                                                                      {"name": "Feedback Due", "count": 0}]},
                                                                  "supervisor_interview": {"total": 0,
                                                                                           "status_counts": [
                                                                                               {"name": "Offer",
                                                                                                "count": 0},
                                                                                               {"name": "Failed",
                                                                                                "count": 0},
                                                                                               {"name": "Cancelled",
                                                                                                "count": 0},
                                                                                               {"name": "Next Round",
                                                                                                "count": 0},
                                                                                               {"name": "Feedback Due",
                                                                                                "count": 0}]},
                                                                  "points": 0.0}}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def list_team_structure(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data based on engineer\'s name.', 'type': openapi.TYPE_STRING},
            {'name': 'filter_json',
             'description': 'JSON to filter data based on various fields like teams, skills etc.',
             'type': openapi.TYPE_OBJECT},
            {'name': 'inter_section',
             'description': 'To filter data based on skillset (if true, will return those records having only'
                            ' particular skill else will return all records that contains the skill).',
             'type': openapi.TYPE_BOOLEAN}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 492, "employee_id": 2877, "employee_name": "Adarsh kumar singh", "shift": "evening",
                 "technology": ["Python", "Nodejs", "JavaScript", "ReactJS"],
                 "current_project": {"count": 1, "project": [{"id": 1228, "consultant": "Chaitanya Upadhayay"}]},
                 "team": {"id": 50, "name": "Dazzlers(Python)"}, "is_scrum": False}], "count": {
                "shift": [{"name": "morning", "display_name": "Morning Shift (6 AM to 3 PM)", "count": 0},
                          {"name": "general", "display_name": "General Shift (10 AM to 7 PM)", "count": 0},
                          {"name": "evening", "display_name": "Evening Shift (5:30 PM to 2:30 AM)", "count": 1},
                          {"name": "afternoon", "display_name": "Afternoon Shift (12 Noon to 9 PM)", "count": 0}],
                "team": [{"display_name": "Training", "count": 0}, {"display_name": "Quartz(Java)", "count": 0},
                         {"display_name": "Kynites(Java)", "count": 0}, {"display_name": "Jaspers(Java)", "count": 0},
                         {"display_name": "Kunzites(Python)", "count": 0},
                         {"display_name": "Emeralds(Python)", "count": 0},
                         {"display_name": "Dazzlers(Python)", "count": 1},
                         {"display_name": "Adamites(Java)", "count": 0}, {"display_name": "Artizens(MEAN)", "count": 0},
                         {"display_name": "Briskers(Python)", "count": 0},
                         {"display_name": "Amethysts(Python)", "count": 0},
                         {"display_name": "Misc : Not active in engineering", "count": 0},
                         {"display_name": "Epimonis", "count": 0}, {"display_name": "CODE", "count": 0},
                         {"display_name": "Awesome", "count": 0}, {"display_name": "Ace", "count": 0},
                         {"display_name": "ODC", "count": 0}, {"display_name": "Product Team", "count": 0},
                         {"display_name": "Delivery", "count": 0}, {"display_name": "Java - Zenith", "count": 0},
                         {"display_name": "Zircons (ELK / Devops)", "count": 0},
                         {"display_name": "Ozrics (ELK / Devops)", "count": 0},
                         {"display_name": "Curators (Python)", "count": 0}],
                "skill": [{"display_name": "Python", "count": 1}, {"display_name": "Java", "count": 0},
                          {"display_name": "Nodejs", "count": 1}, {"display_name": "JavaScript", "count": 1},
                          {"display_name": "ReactJS", "count": 1}, {"display_name": "Angular", "count": 0},
                          {"display_name": "SQL", "count": 0}, {"display_name": "AWS", "count": 0},
                          {"display_name": "DevOps", "count": 0}, {"display_name": "BA", "count": 0},
                          {"display_name": "DA", "count": 0}, {"display_name": "Peoplesoft", "count": 0},
                          {"display_name": "Workday", "count": 0}, {"display_name": "Kronos", "count": 0},
                          {"display_name": "Lawson", "count": 0}, {"display_name": "Full Stack", "count": 0},
                          {"display_name": "Salesforce", "count": 0}, {"display_name": "Cyber Security", "count": 0},
                          {"display_name": "Other", "count": 0}]}, "total": 1}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def retrieve_team_structure(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "data": {"count": 8, "id": 50, "name": "Dazzlers(Python)", "scrum_timing": "08:30 AM - 09:00 AM"}}},
            400: {'description': 'Bad Request', },
        }
    )(view_func)

    return decorated_view


def create_team_structure(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of engineering team.'),
                'scrum_timing': openapi.Schema(type=openapi.TYPE_STRING, description='Scrum timing of the team.')
            },
            ['name', 'scrum_timing']
        ],
        responses={
            201: {'description': 'Success', 'response': {"message": "Team added to log1"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_team_structure(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of engineering team.'),
                'scrum_timing': openapi.Schema(type=openapi.TYPE_STRING, description='Scrum timing of the team.')
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Team Details Updated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_export(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data based on engineer\'s name.', 'type': openapi.TYPE_STRING},
            {'name': 'filter_json',
             'description': 'JSON to filter data based on various fields like teams, skills etc.',
             'type': openapi.TYPE_OBJECT}
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": "https://bugtracking.s3.ap-south-1.amazonaws.com/:44:16.xlsx"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_update_shift(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_ids': openapi.Schema(type=openapi.TYPE_ARRAY, description='List of ids of engineers.',
                                               items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'shift': openapi.Schema(type=openapi.TYPE_STRING, description='Updated shift detail.')
            },
            ['employee_ids', 'shift']
        ],
        responses={
            200: {'description': 'Success', 'response': {"message": "Shift Detail Updated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_teams(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'query', 'description': 'To filter data based on team\'s name.', 'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"count": 7, "id": 34, "name": "Product Team", "scrum_timing": "12:00 PM - 12:30 PM",
                 "scrum_master": [{"id": 551, "employee_name": "Darshan Tiwari"}]}], "total": 1}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_move_employee(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_ids': openapi.Schema(type=openapi.TYPE_ARRAY,
                                               description='List of ids of employee which you want to move.',
                                               items=openapi.Items(type=openapi.TYPE_INTEGER))
            },
            ['employee_ids']
        ],
        responses={
            202: {'description': 'Success', 'response': {"message": "Engineers moved successfully", "not_moved": []}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_update_scrum(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER,
                                              description='ID of the employee whom you want to make scrum master.')
            },
            ['employee_id']
        ],
        responses={
            200: {'description': 'Error', 'response': {"message": "No employee selected"}},
            202: {'description': 'Success',
                  'response': {"message": "Sanidhya Goyal appointed as scrum master for Quartz(Java)"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_remove_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success', 'response': {"message": "Team Removed Successfully"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def team_structure_compare_teams(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {'name': 'team_ids', 'description': 'IDS of engineering teams you want to compare (comma separated)',
             'type': openapi.TYPE_STRING}
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 56, "team_name": "Quartz(Java)", "employee": [
                {"id": 488, "employee_name": "Aaditya sohani"}, {"id": 294, "employee_name": "Aditya Bhardwaj"},
                {"id": 541, "employee_name": "Aman Singh"}, {"id": 525, "employee_name": "Rishabh Goel"},
                {"id": 494, "employee_name": "Sheetal jadoun"}, {"id": 42, "employee_name": "Simrankour Pothiwal"}],
                                                                   "scrum": []},
                                                                  {"id": 55, "team_name": "Kynites(Java)", "employee": [
                                                                      {"id": 493, "employee_name": "Anuj patidar"},
                                                                      {"id": 635, "employee_name": "Isha Gupta"},
                                                                      {"id": 616, "employee_name": "Kushal Kumar Ojha"},
                                                                      {"id": 319, "employee_name": "Muskan Agarwal"},
                                                                      {"id": 617, "employee_name": "Nikhil Yadav"},
                                                                      {"id": 643, "employee_name": "YASHRAJ MANDLOI"},
                                                                      {"id": 489, "employee_name": "Yash agrawal"}],
                                                                   "scrum": []}], "total": 2}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
