import os
from datetime import date

from constance import config
from marketing.models import Interview
from utils_app.utils import create_csv_file
from log1.utils import write_exception, post_msg_using_webhook


def get_display_choice(data, data_type, request):
    try:
        if data_type == 'interview_mode':
            for mode in Interview.INTERVIEW_MODE:
                if data == mode[0]:
                    return mode[1]
            return None
        if data_type == 'screening_type':
            for mode in Interview.TYPE_CHOICES:
                if data == mode[0]:
                    return mode[1]
            return None
    except Exception as error:
        write_exception(error, request)
        return str(error)


def get_status_emoji(status):
    emoji = ''
    if status == 'next_round':
        emoji = ':+1:'
    elif status == 'failed':
        emoji = ':-1:'
    elif status == 'offer':
        emoji = ':v:'
    return emoji


class MessageCard:

    @staticmethod
    def interview_feedback_card(obj, payload, request):
        try:
            marketer = obj.marketer
            marketer_name = f"<@{marketer.slack_id}>" if marketer.slack_id else marketer.employee_name
            status = "NA"
            for i in obj.STATUS_CHOICES:
                if i[0] == obj.status:
                    status = i[1]
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":speech_balloon:  Interview Feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Consultant name:* `{obj.consultant.name}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {get_status_emoji(obj.status)} {status}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"`I-{obj.id}` :: {obj.round if obj.round else 1}R :: "
                                    f"{obj.submission.get_work_type_display()} :: "
                                    f"{get_display_choice(obj.screening_type, 'screening_type', request)} :: "
                                    f"{get_display_choice(obj.interview_mode, 'interview_mode', request)} :: "
                                    f"{obj.start_time.date().strftime('%m/%d/%Y')} :: "
                                    f"{obj.start_time.time().strftime('%H:%M')} EST :: {obj.submission.client} :: "
                                    f"{marketer_name} ::  {obj.submission.marketing_team.name} :: "
                                    f"{obj.submission.lead.position.display_name}"
                        }
                    }
                ]
            }
            for item in payload:
                block = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": item.get('header'),
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": item.get('feedback')
                        }
                    },
                ]
                data['blocks'].extend(block)
            return data
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
                                f"{payload.get('gender')} *Name* :  {consultant.name}\n"
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
                post_msg_using_webhook(
                    config.slack_candidate_feedback_url, data)
            if feedback.feedback_type == 'pre_joining':
                post_msg_using_webhook(
                    config.slack_pre_joining_feedback_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def coder_request_card(payload, request):
        try:
            title = payload.get('title', 'NA')
            interview = payload.get('interview', 'NA')
            supervisor = interview.supervisor
            marketer = interview.submission.created_by
            supervisor_name = f"<@{supervisor.slack_id}>" if supervisor.slack_id else supervisor.employee_name
            marketer_name = f"<@{marketer.slack_id}>" if marketer and marketer.slack_id else marketer.employee_name
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
                                    f"*{interview.submission.consultant.name}*"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Requested by *{marketer_name}* from *{marketer.team.name}*",
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Technology:* {str(interview.tech_stack) if interview.tech_stack else 'NA'}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Supervisor:* {supervisor_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:* `{interview.start_time.strftime('%a, %d %B')}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Time:* `{interview.start_time.strftime('%I:%M %p EST')} - "
                                        f"{interview.end_time.strftime('%I:%M %p EST')}`"
                            }
                        ]
                    },
                ]
            }
            if title == 'Coding Assignment' and interview.guests.all():
                coding_experts = ", ".join(
                    [f"<@{coder.slack_id}>" if coder.slack_id else coder.employee_name for coder in
                     interview.guests.all()]
                )
                block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Coding expert*: {coding_experts}"
                    }
                }
                data['blocks'].append(block)
            if interview.coding_info:
                block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Coding Info*: {interview.coding_info}"
                    }
                }
                data['blocks'].append(block)
            post_msg_using_webhook(config.slack_engineering_url, data)
            return "ok"
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
    def consultant_joined_message_card(payload, request=None):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":white_check_mark:  Project Joined",
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
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Submitted on:* `{payload.get('submitted_on', 'NA')}`"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Employer:* `{payload.get('employer', 'NA')}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Recruiter:* {payload.get('recruiter_name', 'NA')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Joining Count*"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":pushpin: `{payload.get('team_name', 'NA')}` - *{payload.get('team', 'NA')}*  |  `Total` - *{payload.get('total', 'NA')}*"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": "View in Log1"
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}",
                                "value": "click_me_123"
                            }
                        ]
                    }
                ]
            }

            # Sending message on Messaging Tool
            post_msg_using_webhook(payload.get("slack_url"), data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def consultant_independent_message_card(payload, request=None):
        try:
            data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":white_check_mark:  Support Independent",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('activity_title', 'NA')}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Client Name:* {payload.get('client_name', 'NA')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Consultant Name:* {payload.get('consultant_name', 'NA')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Project Start Date:* `{payload.get('project_start_date', 'NA')}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Support End Date:* `{payload.get('support_end_date', 'NA')}`"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Support Duration:* `{payload.get('support_duration', 'NA')}`"
                            }
                        ]
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Feedback By Engineer",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('feedback', 'NA')}"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": "View in Log1"
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/project/{payload.get('project_id')}/",
                                "value": "click_me_123"
                            }
                        ]
                    }
                ]
            }

            # Sending message on Messaging Tool
            post_msg_using_webhook(config.slack_engineering_private_url, data)
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
                            "text": ":small_red_triangle_down: Project Termination Feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{payload.get('sub_title', '')}" + "\n" + f"{payload.get('activity_text', '')}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Project duration:* {payload.get('months', 0)} months"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Employer:* {payload.get('employer', 'NA')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Recruiter:* {payload.get('recruiter_name', 'NA')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* `{payload.get('status', 'NA')}`"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": payload.get('reason', "NA")
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Termination Count:* \n:pushpin: *`{payload.get('team', 'NA')}`* - "
                                    f"*{payload.get('team_count', 'NA')}*  `Total` - *{payload.get('total', 'NA')}*"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "emoji": True,
                                    "text": "View in Log1"
                                },
                                "style": "primary",
                                "url": f"https://app.log1.com/#/details/{payload.get('submission_id')}/"
                                       f"project?id={payload.get('project_id')}",
                                "value": "click_me_123"
                            }
                        ]
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(payload.get('slack_url'), data)

            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_receive_message_card(payload, request=None):
        try:
            project_count = ''
            if payload.get('w2_count', 'NA') != 0:
                project_count += f"*`W2`* - *{payload.get('w2_count', 'NA')}*   "
            if payload.get('c2c_count', 'NA') != 0:
                project_count += f"*`C2C`* - *{payload.get('c2c_count', 'NA')}*   "

            data = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": " ",
                            "emoji": True
                        }
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":v: Offer",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": " ",
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
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Employer:* {payload.get('employer', 'NA')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Start:* `{payload.get('project_start', 'NA')}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Location:* {payload.get('city', 'NA')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Role:* {payload.get('job_title', 'NA')}"
                            },

                            {
                                "type": "mrkdwn",
                                "text": f"*Job Type:* {payload.get('project_type', 'NA')}"
                            },
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Recruiter:* {payload.get('recruiter_name', 'NA')}"
                            },
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Supervisors:*"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"{payload.get('supervisors', 'NA')}"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f":triangular_flag_on_post: *`{payload.get('team', 'NA')}`* - *{payload.get('team_count', 'NA')}*"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"{project_count}    *`Total`* - *{payload.get('total', 'NA')}*"
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
                                    "text": "View in Log1"
                                },
                                "url": f"{config.APP_URL}#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}",
                                "value": "click_me_123"
                            }
                        ]
                    }
                ]
            }
            if payload.get('team') == 'Consultadd Canada':
                slack_url = config.slack_canada_offer_url
            else:
                slack_url = config.slack_usa_offer_url
            post_msg_using_webhook(slack_url, data)
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
                        "type": "divider"
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
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Location*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('city', 'NA'),
                                "emoji": True
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Recruiter*"
                            },
                            {
                                "type": "plain_text",
                                "text": payload.get('recruiter_name', 'NA'),
                                "emoji": True
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Status*"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"`{payload.get('status', 'NA')}`",
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

    # noinspection PyTypeChecker
    @staticmethod
    def interview_data_report(payload, url):
        try:
            card_data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":clipboard: {payload.get('title')}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"`Date : {date.today()}`"
                        }
                    },
                    {
                        "type": "divider"
                    }
                ]
            }

            if not payload.get("data", None):
                card_data['blocks'].append(
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"No Interviews Scheduled.",
                            "emoji": True
                        }
                    }
                )
                res, msg = post_msg_using_webhook(url, card_data)
                return res, msg

            screening_type_headers = payload['data'].keys()
            for header in screening_type_headers:
                if not payload['data'][header]:
                    continue
                card_data['blocks'].append(
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{header}",
                            "emoji": True
                        }
                    }
                )
                sl = 1
                for data in payload['data'][header]:
                    card_data['blocks'].append(
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*`{sl}.`* *CTB:* {data.get('ctb', None)}\n\t   "
                                            f"*Round:* {data.get('round', 1)}\n\t   *Type:* {data.get('type', None)}\n\t"
                                            f"   *Time:* {data.get('start', None).split('::')[1]}\n\t   "
                                            f"*Project Type:* {data.get('project_type')}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"`Consultant` {data.get('consultant')}\n `Client` {data.get('client', None)} "
                                            f"\n `Marketer` {data.get('marketer')}\n `Job` {data.get('position')}"
                                            f"\n `Call Type` {data.get('call_type')}"
                                }
                            ]
                        },
                    )
                    sl += 1
                card_data['blocks'].append(
                    {
                        "type": "divider"
                    }
                )
            card_data['blocks'].append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "emoji": True,
                                "text": "Download CSV"
                            },
                            "style": "primary",
                            "url": payload['file_url'],
                            "value": "click_me_123",
                            "action_id": "button-action"
                        }
                    ]
                }
            )
            res, msg = post_msg_using_webhook(url, card_data)
            return res, msg
        except Exception as error:
            return error, "error"

    @staticmethod
    def pool_candidate_report(payload, url):
        try:
            if payload.get('data') is None:
                return "No data to display", "ok"
            file_url = create_csv_file(payload)
            card_data = {}
            head_block = {
                "type": "header",
                "text": {
                    "emoji": True,
                    "type": "plain_text",
                    "text": f":memo: Pool Candidates\t   \t   {date.today().strftime('%d %b, %Y')}"
                }
            }
            content_len = len(payload['data'])
            portions = int(content_len / 15) + 1
            first, last = 0, 15
            for portion in range(0, portions):
                sl = 1
                card_data['blocks'] = []
                if payload['data'][first: last]:
                    card_data['blocks'].append(head_block)
                for data in payload['data'][first: last]:
                    if sl < 10:
                        first_column = f"`{sl}.` *Consultant:* {data.get('consultant', None)}\n\t   " \
                                       f"*Team:* {data.get('team')}\n\t   *Skills*: {data.get('skills')}"
                    else:
                        first_column = f"`{sl}.` *Consultant:* {data.get('consultant', None)}\n\t    " \
                                       f"*Team:* {data.get('team')}\n\t    *Skills*: {data.get('skills')}"

                    card_data['blocks'].append(
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": first_column
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"`Days` {data.get('days')}\n `Recruiter` {data.get('recruiter', None)} "
                                            f"\n `Marketer` {data.get('marketer')}\n `Open Offer` {data.get('open_offer')}"
                                }
                            ]
                        },
                    )
                    sl += 1
                if payload['data'][first: last]:
                    card_data['blocks'].append(
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "emoji": True,
                                        "text": "Download CSV"
                                    },
                                    "style": "primary",
                                    "url": file_url,
                                    "value": "click_me_123",
                                    "action_id": "button-action"
                                }
                            ]
                        },
                    )
                    post_msg_using_webhook(url, card_data)
                first = last
                data_left = content_len - (portion + 1) * 15
                last = last + 16 + data_left if data_left <= 20 else last + 16
            print(content_len)
        except Exception as error:
            return error, "error"

    # noinspection PyTypeChecker
    @staticmethod
    def marketing_leaderboard(payload, url):
        try:
            card_data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":onsultadd:  Consultant Compete  :onsultadd:",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"`{payload['competition_day']}th` *Day Of Competition Leaderboard*"
                        }
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            for rank in range(1, payload["positions"] + 1):
                offer = True if 'offer' in payload["data"][rank] else False
                interview = True if 'interview' in payload["data"][rank] else False
                submission = True if 'submission' in payload["data"][rank] else False

                if submission:
                    section_text = \
                        f":submission: *Highest No Of Submissions*\n*Name:* {payload['data'][rank]['submission']['name']}" \
                        f"\n*Team Name :* `{payload['data'][rank]['submission']['team']}`" \
                        f"\n*Count:* `{payload['data'][rank]['submission']['score']}`"
                else:
                    section_text = f":submission: *Highest No Of Submissions*\n`No Submissions Recorded Yet`"

                if rank > 1 and not offer and not submission and not interview:
                    break

                card_data["blocks"].append(
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":medal: Top {rank}",
                            "emoji": True
                        }
                    }
                )
                card_data["blocks"].append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": ":Offer: *Highest No Of Offers*" if offer else ":submission: *Highest No Of Submission*" if submission else ":Offer: *Highest No Of Offers*"
                            },
                            {
                                "type": "mrkdwn",
                                "text": ":interview: *Highest No Of Interviews*"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Name*: {payload['data'][rank]['offer']['name']}" if offer else f"*Name*: {payload['data'][rank]['submission']['name']}" if submission else "`No Offers Recorded Yet`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Name*: {payload['data'][rank]['interview']['name']}" if interview else "`No Interviews Recorded Yet`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Team Name*: `{payload['data'][rank]['offer']['team']}`" if offer else f"*Team Name*: `{payload['data'][rank]['submission']['team']}`" if submission else ""
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Team Name*: `{payload['data'][rank]['interview']['team']}`" if interview else ""
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Count*: `{payload['data'][rank]['offer']['score']}`" if offer else f"*Count*: `{payload['data'][rank]['submission']['score']}`" if submission else ""
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Count*: `{payload['data'][rank]['interview']['score']}`" if interview else ""
                            }
                        ]
                    }
                )

                if offer:
                    card_data["blocks"].append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": section_text
                            }
                        }
                    )
                card_data["blocks"].append(
                    {
                        "type": "divider"
                    }
                )

            if 'offer' not in payload["data"][1]:
                card_data["blocks"].append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Zero* *offers*, *time's* *running* *out!* *Determine*, *explore*, *take* *action!* :hourglass_flowing_sand: :rocket:"
                        }
                    }
                )
            else:
                card_data["blocks"].append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f":Offer: *Total No Of Offers:*  `{payload['total_offers']}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f":Offer: *Total No Of Offers in pipeline:*  `{payload['offers_in_pipeline']}`"
                            }
                        ]
                    }
                )
                card_data["blocks"].append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f":interview: *Total No Of Interviews:*  `{payload['total_interview']}`\n"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f":submission: *Total No Of Submissions:*  `{payload['total_submission']}`\n"
                            }
                        ]
                    }
                )
            res, msg = post_msg_using_webhook(url, card_data)
            return res, msg
        except Exception as error:
            return error, "error"

    @staticmethod
    def send_test_feedback(payload, url):
        try:
            coders, reviewed_by = "", ""
            for i in payload.get('coders'):
                coders = coders + " " + f"`{i}`"

            for j in payload.get('reviewed_by'):
                reviewed_by += f"`{j}`  "

            if payload.get('type').capitalize() == 'Offline':
                engineering_feedback = f"*Submitted By:*  {coders}\n " \
                                    f"*Reviewed By:*   {reviewed_by} \n" \
                                    f"*Performance Rating:* {payload.get('coder_rating')} \n " \
                                    f"*Feedback*:  {payload.get('coder_remark')}"
            else:
                engineering_feedback = f"*Submitted By:*  {coders}\n " \
                                    f"*Performance Rating:* {payload.get('coder_rating')} \n " \
                                    f"*Feedback*:  {payload.get('coder_remark')}"

            if payload.get('emoji') == ":x:":
                block_header = "Reason of Cancellation"
                block_subject = f"*Provided By:* `{payload.get('marketer')}` \n*Reason:* {payload.get('cancel_reason')}"
            else:
                block_header = "Marketer Feedback"
                block_subject = f"*Marketer Name:* `{payload.get('marketer')}` \n*Feedback:* {payload.get('feedback')}"
            card_data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":speech_balloon:  Test Feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Consultant name:* `{payload.get('consultant_name')}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {payload.get('emoji')} {payload.get('status')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"`TST-{payload.get('id')}` :: {payload.get('client')} :: {payload.get('vendor')} ::"
                                    f" {payload.get('type').capitalize()}"
                        }
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": " :computer: Engineer Feedback",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": engineering_feedback
                        }
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":lower_left_fountain_pen:  {block_header}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{block_subject}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Please click button to redirect to Test Details* "
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Test Details",
                                "emoji": True
                            },
                            "value": "click_me_123",
                            "url": f"{payload.get('test_url')}",
                            "action_id": "button-action"
                        }
                    },
                    {
                        "type": "divider"
                    }
                ]
            }
            res, msg = post_msg_using_webhook(url, card_data)
            return res, msg
        except Exception as error:
            return False, error

    @staticmethod
    def daily_supervisor_interview(payload):
        try:
            if payload.get('data') is None:
                return "No data to display", False
            card_data = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":clipboard: {payload.get('title')}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"`Date : {date.today()}`"
                        }
                    },
                    {
                        "type": "divider"
                    }
                ]
            }

            screening_type_headers = payload['data'].keys()
            for header in screening_type_headers:
                if not payload['data'][header]:
                    continue
                card_data['blocks'].append(
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{header}",
                            "emoji": True
                        }
                    }
                )
                sl = 1
                for data in payload['data'][header]:
                    data_block = {"blocks": [{
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"`{sl}.` "
                                        f"*Round:* {data.get('round', 1)}\n\t   *Type:* {data.get('type', None)}\n\t"
                                        f"   *Time:* {data.get('start', None).split('::')[1]}\n\t   "
                                        f"*Project Type:* {data.get('project_type')}\n\t   "
                                        f"*Duration:* {data.get('duration')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"`Consultant` {data.get('consultant')}\n `Client` {data.get('client', None)} "
                                        f"\n `Marketer` {data.get('marketer')}\n `Job` {data.get('position')}"
                                        f"\n `Call Type` {data.get('call_type')}"
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
                                        "text": f"Redirect I-{data.get('interview_id')}"
                                    },
                                    "style": "primary",
                                    "url": data.get('redirect_link'),
                                    "value": "click_me_123",
                                    "action_id": "button-action"
                                }
                            ]
                        },
                        {
                            "type": "divider"
                        }
                    ]}
                    card_data['blocks'].extend(data_block.get('blocks'))
                    sl += 1
            return card_data, True
        except Exception as error:
            return error, False
