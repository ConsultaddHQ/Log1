import os

import boto3
from constance import config
from utils_app.utils import create_csv_file
from log1.utils import write_exception, post_msg_using_webhook


def get_element(element_type, data=None):
    if data is None:
        data = {}
    divider_set = {
        "type": "divider"
    }
    header_set = {
        "type": "header",
        "text":
            {
                "type": "plain_text",
                "text": data.get('title', None),
                "emoji": True
            }
    }
    column_set = {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*{data.get('question', None)}*\n{data.get('answer', None)}"
            }
        ]
    }
    section_set = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{data.get('question', None)}*\n{data.get('answer', None)}"
        }
    }
    element_set = {
        "type": "mrkdwn",
        "text": f"*{data.get('question')}*\n{data.get('answer')}"
    }
    context_set = {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": " "
            }
        ]
    }
    if element_type == "element_set":
        return element_set
    elif element_type == "column_set":
        return column_set
    elif element_type == "section_set":
        return section_set
    elif element_type == "header_set":
        return header_set
    elif element_type == "divider_set":
        return divider_set
    elif element_type == "context_set":
        return context_set
    return None


class MessageCard:

    @staticmethod
    def interview_feedback_card(interview_data, header_names, request):
        try:
            header_position = 0
            card_data = {"blocks": []}
            body = card_data['blocks']
            for data_set, header_name in zip(interview_data, header_names):
                column_length = 2
                body.append(get_element('header_set', {"title": header_name}))
                for data, count in zip(data_set, range(0, len(data_set))):
                    if type(data.get('answer')) is str:
                        data['answer'] = data.get('answer').replace('[', '').replace(']', '').replace('"', '') \
                            .replace('\n', '')
                    if data.get('answer_type') == 'long_text':
                        body.append(get_element("section_set", data))
                        count -= 1
                    elif count % column_length != 0:
                        body[-1]['fields'].append(get_element("element_set", data))
                    else:
                        body.append(get_element("column_set", data))
                body.append(get_element('divider_set'))
                header_position += 1
            card_data['blocks'].append(get_element('context_set'))
            return card_data
        except Exception as error:
            write_exception(message=error, request=request)
            return error

    @staticmethod
    def exit_interview_card(payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Exit interview for {payload.get('consultant', 'NA')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Reason for leaving* : {payload.get('reason', 'NA')} \n "
                                    f"*Termination Date* : {payload.get('termination_date', 'NA')} \n "
                                    f"*Exit Interview Details* : {payload.get('exit_details', 'NA')} \n "
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": " "
                            }
                        ]
                    }
                ]
            }
            post_msg_using_webhook(config.slack_exit_interview_url, data)
            return 'sent'
        except Exception as error:
            write_exception(message=error, request=request)
            return error

    @staticmethod
    def new_recruit_card(consultant, payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "New Recruit on Bench :the_horns::smile::the_horns:"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text":
                                f"*Consultant*\n"
                                f"{payload.get('gender')} *Name* :  {consultant}\n"
                                f"{payload.get('gender')} *Email* :  {consultant.email}\n"
                                f"{payload.get('recruiter_gender')} *Recruiter* :  {payload.get('recruiter_name', 'NA')}\n"
                                f"✨ *Profile* :  {consultant.skills} \n"
                                f"🇺🇸 *Visa* :  {payload.get('visa', 'NA')}\n"
                                f"✨ *Source* :  {payload.get('source', 'NA')}\n"
                                f"✨ *Rate* : {payload.get('rate', 'NA')} \n"
                                f"🇺🇸  *Current Location* :  {consultant.current_city} \n"
                                f"✨ *Team* :  {payload.get('recruiter_team', 'NA')} \n"
                                f"✨ *CFR* :  {payload.get('cfr', 'NA')} \n"
                                f"✨ *Feedback* :  {payload.get('feedback', 'NA')}\n"
                                f"\n Recruit Count of {payload.get('recruiter_team', 'NA')} for this month - {payload.get('team_count', 'NA')}"
                                f"\n Total Recruit Count of this month - {payload.get('total_count', 'NA')}"
                        },
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": " "
                            }
                        ]
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_new_recruit_on_bench, data)
        except Exception as error:
            write_exception(message=error, request=request)
            return error

    @staticmethod
    def feedback_card(feedback, request=None):
        try:
            project = feedback.project
            if hasattr(project, 'submission'):
                text = f":: {project.submission.lead.job_title} ::" if project.submission.lead else "::"
                title = f"{project.consultant.name} {text} {project.submission.client}"
            else:
                title = feedback.consultant.name
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text":
                            {
                                "emoji": True,
                                "type": "plain_text",
                                "text": f"*{title}*"
                            }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": feedback.description,
                            "emoji": True
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": " "
                            }
                        ]
                    }
                ]
            }
            if feedback.feedback_type == 'engineering_issue':
                post_msg_using_webhook(config.slack_candidate_feedback_url, data)
            if feedback.feedback_type == 'pre_joining':
                post_msg_using_webhook(config.slack_pre_joining_feedback_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def coder_request_card(payload, request):
        try:
            title = payload.get('title', 'NA')
            interview = payload.get('interview', 'NA')
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": title,
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"I-{interview.id} : Interview from *{interview.submission.client}* for "
                                    f"*{interview.submission.consultant.name}* \n"
                                    f"Requested by *{interview.submission.created_by.employee_name}* from "
                                    f"*{interview.submission.created_by.team.name}*",
                        },
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Technology*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.tech_stack) if interview.tech_stack else "NA",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Supervisor*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.supervisor.employee_name),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Date*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.start_time.strftime('%a, %d %B')),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Time*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                        f"{interview.end_time.strftime('%I:%M %p EST')}",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            if interview.coding_info:
                data_len = len(data['blocks'])
                data['blocks'].insert(data_len - 2, {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Coder's Info*"
                        },
                        {
                            "type": "plain_text",
                            "text": interview.coding_info,
                            "emoji": True
                        }
                    ]
                },
                                      )
            post_msg_using_webhook(config.slack_engineering_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def coder_assigned_card(interview, request):
        try:
            coding_experts = ", ".join(interview.guest.all().values_list('employee_name', flat=True))
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Coding Assignment",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"I-{interview.id} : Interview from *{interview.submission.client}* for "
                                    f"*{interview.submission.consultant.name}* \n"
                                    f"Requested by *{interview.submission.created_by.employee_name}* from "
                                    f"*{interview.submission.created_by.team.name}*",
                        },
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Technology*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.tech_stack),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Supervisor*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.supervisor.employee_name),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Date*"
                            },
                            {
                                "type": "plain_text",
                                "text": str(interview.start_time.strftime('%a, %d %B')),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Time*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                        f"{interview.end_time.strftime('%I:%M %p EST')}",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Coding expert*"
                            },
                            {
                                "type": "plain_text",
                                "text": coding_experts,
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            post_msg_using_webhook(config.slack_engineering_url, data)
            return 'ok'
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def test_received_card(payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Test Received",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('subtitle', 'NA')}\n{payload.get('activity_text', 'NA')}"
                        },
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Timezone*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('timezone', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Deadline*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('deadline', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            post_msg_using_webhook(config.slack_engineering_url, data)
            return 'ok'
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def get_simple_card(payload):
        data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": payload.get("title"),
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": payload.get("body")
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": " "
                        }
                    ]
                }
            ]
        }
        return data

    @staticmethod
    def consultant_joined_message_card(payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Project Joined",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('activity_title', 'NA')}\n{payload.get('activity_text', 'NA')}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " "
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Submitted On*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{payload.get('submitted_on', 'NA')}",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Employer*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('employer', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Recruiter*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": f"{payload.get('team_name', 'NA')} - {payload.get('team', 'NA')}"
                                },
                                "style": "primary",
                                "value": "click_me_123",
                                "url": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": f"Total - {payload.get('total', 'NA')}"
                                },
                                "style": "primary",
                                "value": "click_me_123",
                                "url": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Log1",
                                    "emoji": True
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}",
                                "value": "click_me_123",
                                "action_id": "actionId-0"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_joined_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_termination_message_card(payload, request):
        try:

            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Project Termination Feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('activity_sub_title', '')}\n{payload.get('activity_text', '')}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " "
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Project duration*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{payload.get('months', 0)} months",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Employer*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('employer', "NA"),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Location*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('project.city', "NA"),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Recruiter*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', "NA"),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Status*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('status', "NA"),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Feedback*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('reason', "NA"),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Log1",
                                    "emoji": True
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/"
                                       f"project?id={payload.get('project_id')}",
                                "action_id": "actionId-0"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_project_termination_url, data)

            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_receive_message_card(payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Offer",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Paper work* received from *{payload.get('client')}* for "
                                    f"*{payload.get('consultant')}*\n{payload.get('activity_text')}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " "
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Employer*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('employer', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Start Date*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('project_start', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Location*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('city', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Role*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('job_title', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Recruiter*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Supervisors*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('supervisors', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": f"{payload.get('employer', 'NA')} - {payload.get('team', 'NA')}"
                                },
                                "style": "primary",
                                "value": "click_me_123",
                                "url": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": f"Total - {payload.get('total', 'NA')}"
                                },
                                "style": "primary",
                                "value": "click_me_123",
                                "url": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Log1",
                                    "emoji": True
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}",
                                "value": "click_me_123",
                                "action_id": "actionId-0"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }

            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_offer_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_cancellation_message_card(payload, request):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Offer cancellation feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('activity_sub_title', '')}\n{payload.get('activity_text', '')}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " "
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Employer*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('employer', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Location*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('city', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Recruiter*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Status*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Feedback*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('reason', 'NA'),
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Log1",
                                    "emoji": True
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}",
                                "action_id": "actionId-0"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "plain_text",
                                "text": " ",
                                "emoji": True
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_offer_failure_url, data)

            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def data_report(payload, url):
        file_url = create_csv_file(payload)
        card_data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":MEMO: Interview Scheduled for today",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                }
            ]
        }
        for data in payload['data']:
            card_data['blocks'].append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": f"CTB-{data.get('ctb', None)}  ::  Round-{data.get('round', 1)}  ::  "
                                    f"Type-{data.get('type', None)}  ::  Start Time-{data.get('start', None)}  ::  "
                                    f"Consultant-{data.get('consultant')}  ::  Client-{data.get('client', None)} ::  "
                                    f"Marketer-{data.get('marketer')}  ::  Job Position-{data.get('position')}",
                            "emoji": True
                        },
                    ]
                },
            )
            card_data['blocks'].append({
                "type": "divider"
            })
        card_data['blocks'].append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Click on the button to download csv file"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Click Me",
                        "emoji": True
                    },
                    "url": file_url,
                    "value": "click_me_123",
                    "action_id": "button-action"
                }
            },
        )
        card_data['blocks'].append({
            "type": "divider"
        })
        res, msg = post_msg_using_webhook(url, card_data)
        return res, msg
