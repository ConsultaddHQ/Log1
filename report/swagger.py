from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def report_scrum_meeting(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"message": "message sent"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def report_set_meeting(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            201: {'description': 'Success', 'response': {"message": "success"}}
        }
    )(view_func)

    return decorated_view


def cmd_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': 'API Key.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'text',
                'description': 'Data type and consultant name.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'command',
                'description': 'Command.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "text": "#### Consultant POC :memo: \n\ncommand - data poc rohit\n\n| Name | Email | Status | Team | Marketer | Recruiter | Retention |\n|:-----|:------|:-------|:-----|:---------|:----------|:----------|\n| Rohit Thakur | rohitthakur8@hotmail.com |  on_bench | NetResolute | Nikhil Kumar Sinha |  sumedha keshavabhatla |  Abhimanyu Shekhawat |\n| Rohit Shrivastava | rohit8shrivastava@gmail.com |  on_project | None | None |  Nupur Pandit |  Kriti Sehgal |\n| Rohit Nanawati | nanawatirohit@gmail.com |  on_project | None | None |  Simran Subba Nembang |  Nikita Agarwal |\n| Rohit Surana | rohit.s@consultadd.com |  on_project | None | None |  None |  Nikita Agarwal |\n| Rohit Jain | rohit.j@consultadd.in |  on_project | None | None |  None |  None |\n"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def cmd_marketer(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': 'API Key.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'text',
                'description': 'Data type and marketer name.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'command',
                'description': 'Command.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "text": "#### Marketer Status :memo: \n\nDate Range - 2023-08-13 - 2023-09-12\n\ncommand - data poc arun\n\n| Name | Team | Submission | Interview | Offer | Consultant Assigned |\n|:-----|:-----|:-----------|:----------|:------|:--------------------|\n| Arun Kumar | OC10 |  0 | 0 | 0 |  Vineet Khodre, Dhanashree Ajay Kharade, Nikunj Ganpatbhai Patel, Akhil Babu Karlapudi, Nihit Kumar Singh, Aakash Sethi, Vedang Chandrakant Barhate, Kriti Shree, Aishwarya Soma, Akhil Meda Vasduevamurthy |\n"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def cmd_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': 'API Key.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'text',
                'description': 'arguments.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'command',
                'description': 'Command.',
                'type': openapi.TYPE_STRING,
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {
                "text": "#### Team Status :memo: \n\nFrom Date - 2023-08-13 to 2023-09-12\ncommand - data month\n\n| Team Name | Scrum Master | Current Bench | Submission | Interview | Offer | Joined |\n|:----------|:-------------|:--------------|:-----------|:----------|:------|:-------|\n| Boto3 | Harsh Raj, Sona Singh | 16 | 0 | 0 | 0 | 0  |\n| Induci | Aman Kumar Singh | 22 | 0 | 0 | 0 | 0  |\n| Ioneq | Akshay Mishra | 21 | 0 | 0 | 0 | 0  |\n| Netresolute | Vinal Khelani | 24 | 0 | 0 | 0 | 0  |\n| Oc10 | Arun Kumar | 21 | 0 | 0 | 0 | 0  |\n| Pythonwise | Mohmmad Junaid | 17 | 0 | 0 | 0 | 0  |\n| Zioqu | Nupur Malhotra | 16 | 0 | 0 | 0 | 0  |\n| Account Management | Kamran Adil | 2 | 0 | 0 | 0 | 0  |\n| Consultadd Canada | Arpit Mehta | 7 | 0 | 0 | 0 | 0  |\n| Jla | None | 0 | 0 | 0 | 0 | 0  |\n| Elegant | None | 0 | 0 | 0 | 0 | 0  |\n| Elegantc | None | 0 | 0 | 0 | 0 | 0  |\n| Elegant Team | Suraj Pagare | 1 | 0 | 0 | 0 | 0  |\n| J&K | None | 0 | 0 | 0 | 0 | 0  |\n| Total | Sudeep B. | 122 | 0 | 1 | 0 | 0 |\n"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_support_report(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'status',
                'description': 'To filter data based on project status.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'query',
                'description': 'To filter data based on some query.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'filter_by_tech',
                'description': 'To filter data based on technology (ba/dev).',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 913, "created": "2022-10-07T13:46:53.052721Z", "end": None, "start": "2022-09-12",
                 "feedback": "", "status": "active", "client": "Newton Principal Agency",
                 "consultant": {"name": "Satyam Kumar Singh", "email": "satyam.k@consultadd.com", "contact": None},
                 "technology": None, "support": {"id": 614, "employee_id": 2933, "email": "alturi.s@consultadd.com",
                                                 "employee_name": "Atluri Soma Sekhara Reddy",
                                                 "team": "Kunzites(Python)", "roles": ["engineer"], "gender": "male",
                                                 "phone": "917659884512", "avatar": None, "is_superuser": False,
                                                 "technology": []}, "joining_date": "2022-09-12",
                 "frequency": "active"}], "counts": {"total": 147, "active": 56, "training": 0, "terminated": 335,
                                                     "less_active": 5, "independent": 47},
                "page_count": {"total": 196, "active": 57, "training": 0,
                               "terminated": 490, "less_active": 6,
                               "independent": 50}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_marketer(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'Max created date of Submission, Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Min created date of Submission, Interview, Project.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'query',
                'description': 'To filter data based on some employee name.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'export',
                'description': 'To export data or not.',
                'type': openapi.TYPE_BOOLEAN,
            },
            {
                'name': 'filter_by_team',
                'description': 'To filter data based on team name.',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 929, "offer": 0, "team": "Pythonwise", "submission": 0, "employee_name": "Aarif Khan Pathan",
                 "unique_interview": 0, "repeat_interview": 0,
                 "consultant_assigned": "Komal Patel, Sangeeta Balchandani, Anam Khan, Somjeet Das Gupta, Ashwin Mulatkar, Richa Mistry, Akriti Mishra, Prajakta Appa Sawant, Nihal Sanjesh Patel, Amsaveni Varadharajan, Tania Sethi"}],
                "total": 248, "file_url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_team(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'Max created date of Submission, Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Min created date of Submission, Interview, Project.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'export',
                'description': 'To export data or not.',
                'type': openapi.TYPE_BOOLEAN,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 2, "team": "Boto3", "offer_count": 3, "scrum_master": "Harsh Raj, Sona Singh", "joined_count": 2,
                 "interview_count": 45, "bench_consultant": 16, "submission_count": 383, "termination_count": 2}],
                "file_url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_team_data(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'Max created date of Submission, Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Min created date of Submission, Interview, Project.',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {
                "data": [{"display_name": "Submission Count", "count": 7537, "default": 7537},
                         {"display_name": "Interview Count", "count": 766, "default": 7537},
                         {"display_name": "Offer Count", "count": 138, "default": 7537},
                         {"display_name": "Joined Count", "count": 126, "default": 7537},
                         {"display_name": "Termination Count", "count": 69, "default": 7537}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_consultant(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'query',
                'description': 'To filter data based on consultant name.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'export',
                'description': 'To export data or not.',
                'type': openapi.TYPE_BOOLEAN,
            },
            {
                'name': 'filter_by_team',
                'description': 'To filter data based on marketing team name.',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 238, "days": 119, "teams": "Pythonwise", "recruiter": "Richa Mistry", "submission_count": 234,
                 "preferred_location": "Boston/Cambridge, New York, California, Las Vegas, Sattle(Washington), Chicago(IL)",
                 "email": "jdhanani69@gmail.com", "status": "on_project", "project_count": 6, "phone_no": "12019124187",
                 "interview_count": 19, "name": "Janki Vibhakarbhai Dhanani"}], "total": 122, "file_url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_supervisor(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'Max created date of Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Min created date of Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'export',
                'description': 'To export data or not.',
                'type': openapi.TYPE_BOOLEAN,
            },
            {
                'name': 'query',
                'description': 'To filter data based on supervisor name.',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 427, "name": "Vishwajeet Thakur", "interviews": 20, "email": "vishwajeet.t@consultadd.com",
                 "pass": 19, "technology": ["Python", "SQL", "AWS", "Terraform"], "fail": 1,
                 "team": "Briskers(Python)"}], "total": 36, "file_url": ""}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def marketing_report_compare_supervisors(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'end',
                'description': 'Max created date of Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'start',
                'description': 'Min created date of Interview.',
                'type': openapi.TYPE_STRING,
            },
            {
                'name': 'supervisors',
                'description': 'List of IDS of supervisors.',
                'type': openapi.TYPE_STRING,
            },

        ],
        responses={
            200: {'description': 'Success', 'response': {"max_rounds": 5, "data": [
                {"id": 427, "name": "Vishwajeet Thakur",
                 "rounds": [{"pass": 77, "fail": 65}, {"pass": 24, "fail": 26}, {"pass": 8, "fail": 7},
                            {"pass": 2, "fail": 0}, {"pass": 0, "fail": 1}]}, {"id": 316, "name": "Vishal Rathod",
                                                                               "rounds": [{"pass": 8, "fail": 2},
                                                                                          {"pass": 5, "fail": 2},
                                                                                          {"pass": 2, "fail": 1}]}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def engineers_project_support(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': 'API Key.',
                'type': openapi.TYPE_STRING,
                'required': True
            },
            {
                'name': 'emi_id',
                'description': 'Employee ID of engineer.',
                'type': openapi.TYPE_INTEGER,
            },
            {
                'name': 'project_id',
                'description': 'ID of project.',
                'type': openapi.TYPE_INTEGER,
            },

        ],
        responses={
            200: {'description': 'Success',
                  'response': {"emp_info": {"name": "Mehul Jain", "emp_id": 2616, "email": "mehul.j@consultadd.com"},
                               "cycle_duration": "July to December", "data": {
                          "project_1": {"status": "Active", "support_start": "2022-09-06", "support_end": None,
                                        "handover_received": False, "handover_given": False, "is_remote": True,
                                        "client": "Charter Communication.", "support_id": 911, "skills": "NA",
                                        "support_duration": 0, "training_duration": "0 days",
                                        "project_start": "2022-09-12", "consultant_name": "Suhas Jadhav",
                                        "project_id": 1184},
                          "project_2": {"status": "Independent", "support_start": "2021-07-26", "support_end": None,
                                        "handover_received": False, "handover_given": False, "is_remote": False,
                                        "client": "Chs", "support_id": 544, "skills": "Java", "support_duration": 0,
                                        "training_duration": "0 days", "project_start": "2021-06-07",
                                        "consultant_name": "Sanjay Ranjit", "project_id": 773},
                          "project_3": {"status": "Independent", "support_start": "2020-09-03", "support_end": None,
                                        "handover_received": False, "handover_given": False, "is_remote": False,
                                        "client": "Cisco", "support_id": 273, "skills": "NA", "support_duration": 0,
                                        "training_duration": "0 days", "project_start": "2020-09-28",
                                        "consultant_name": "Nalanda Magam", "project_id": 548},
                          "project_4": {"status": "Independent", "support_start": "2020-11-09", "support_end": None,
                                        "handover_received": False, "handover_given": False, "is_remote": None,
                                        "client": "Neiman-Marcus", "support_id": 392, "skills": "NA",
                                        "support_duration": 0, "training_duration": "0 days",
                                        "project_start": "2020-11-02", "consultant_name": "Ferry Phooldeep Sharma",
                                        "project_id": 586}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
