import os

from constance import config
from log1.utils import write_exception, post_msg_using_webhook
from utils_app.calendar import get_profile_picture


def get_element(element_type, data={}):
    blank_set = {
        "type": "Column", "width": 50, "items": []
    }
    element = {
        "type": "TextBlock", "text": "", "wrap": True, "spacing": "None"
    }
    row_set = {
        "type": "Column",
        "width": 50,
        "items": [
            {
                "type": "TextBlock",
                "text": data.get('question'),
                "wrap": True,
                "weight": "Bolder"
            }
        ]
    }
    column_set = {
        "type": "ColumnSet",
        "columns": []
    }
    empty_container = {"type": "Container", "items": []}
    container = {
        "type": "Container",
        "items": [
            {
                "size": "Large",
                "color": "Dark",
                "weight": "Bolder",
                "spacing": "Large",
                "type": "TextBlock",
                "text": data.get('name', None)
            }
        ],
        "style": "accent",
        "spacing": "Large"
    }

    if data.get('answer') in ['Yes', 'yes']:
        data['answer'] = "✓ Yes"
        element['color'] = "Good"
    elif data.get('answer') == 'No':
        data['answer'] = "❌ No"
        element['color'] = "Attention"

    if type(data.get('answer')) is list:
        for i in data['answer']:
            row_set["items"].append({"type": "TextBlock", "text": i, "wrap": True, "spacing": "None"})
    elif data.get('answer', None):
        element['text'] = data.get('answer')
        row_set["items"].append(element)
    else:
        element['text'] = "NA"
        row_set["items"].append(element)

    if element_type == "blank_set":
        return blank_set
    if element_type == "row_set":
        return row_set
    elif element_type == "container":
        return container
    elif element_type == "empty_container":
        return empty_container
    elif element_type == "column_set":
        if data:
            column_set["columns"].append(row_set)
        return column_set
    return None


class MessageCard:

    @staticmethod
    def interview_feedback_card(interview_data, container_names, request):
        try:
            container = 0
            card_data = {
                "title": "Interview Feedback",
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.5",
                            "body": []
                        }
                    }
                ]
            }
            body = card_data['attachments'][0]['content']["body"]

            for data_set in interview_data:
                column_length = 3 if container < 2 else 2
                row = 0
                if container % 2 == 0:
                    body.insert(container, get_element('container', {"name": container_names[container]}))
                    container = container + 1
                body.insert(container, get_element('empty_container', {}))

                for data, count in zip(data_set, range(0, len(data_set))):
                    if type(data.get('answer')) is str:
                        data['answer'] = data.get('answer').replace('[', '').replace(']', '').replace('"', '') \
                            .replace('\n', '')
                    if data.get('answer_type') == 'long_text':
                        body[container]["items"].append(get_element("column_set", data))
                        row += 1
                    elif count % column_length != 0:
                        body[container]["items"][row]["columns"].append(get_element("row_set", data))
                    else:
                        body[container]["items"].append(get_element("column_set", data))
                        row += 1 if count != 0 else row
                    if len(data_set) % column_length != 0 and count + 1 == len(data_set) and data.get(
                            'answer_type') != 'long_text':
                        body[container]["items"][row]["columns"].append(get_element("blank_set"))
                container += 1
            return card_data
        except Exception as error:
            write_exception(error, request)

    @staticmethod
    def exit_interview_card(payload, request):
        try:
            data = {
                "title": f"Exit interview for {payload.get('consultant', 'NA')}",
                "text": f"**Reason for leaving** : {payload.get('reason', 'NA')} \n "
                        f"**Termination Date** : {payload.get('termination_date', 'NA')} \n "
                        f"**Exit Interview Details** : {payload.get('exit_details', 'NA')} \n "
            }
            post_msg_using_webhook(config.exit_interview_url, data)
            return 'sent'
        except Exception as error:
            write_exception(message=error, request=request)
            return error

    @staticmethod
    def new_recruit_card(consultant, payload, request):
        try:
            data = {
                "title": "New Recruit on Bench  &#129304;&#128516;&#129304;",
                "text": f"**Consultant**\n"
                        f"{payload.get('consultant_gender')} *Name* :  {consultant}\n"
                        f"{payload.get('consultant_gender')} *Email* :  {consultant.email}\n"
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

            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.new_recruit_on_bench, data)
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
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",
                "themeColor": "#0076D7",
                "@context": "http://schema.org/extensions",
                "type": "header",
                "summary": f"***Engineering Issue***",
                "sections": [{
                    "activityTitle": f"***{title}*** ",
                    "activitySubtitle": f"***Engineering Issue feedback by {request.user.employee_name}***",
                    "activityText": feedback.description, "activityImage": profile_path,
                    "markdown": True}]}

            if feedback.feedback_type == 'engineering_issue':
                post_msg_using_webhook(config.candidate_feedback_url, data)
            if feedback.feedback_type == 'pre_joining':
                post_msg_using_webhook(config.pre_joining_feedback_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def coder_request_card(payload, request):
        try:
            title = payload.get('title', 'NA')
            interview = payload.get('interview', 'NA')
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",

                "themeColor": "#0076D7",
                "@context": "http://schema.org/extensions",
                "summary": f"Coding assignment",
                "sections": [
                    {
                        "activityTitle": title,
                        "activitySubtitle": f"I-{interview.id} : Interview from ***{interview.submission.client}*** for "
                                            f"***{interview.submission.consultant.name}*** ",
                        "activityText": f"Requested by ***{interview.submission.created_by.employee_name}*** from "
                                        f"***{interview.submission.created_by.team.name}***",
                        "activityImage": profile_path,
                        "facts": [
                            {
                                "name": f"Technology",
                                "value": f"{interview.tech_stack}"
                            },
                            {
                                "name": f"Supervisor",
                                "value": f"{interview.supervisor.employee_name}"
                            },
                            {"name": f"Date",
                             "value": f"{interview.start_time.strftime('%a, %d %B %Y')}"
                             }, {"name": f"Time",
                                 "value": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                 }]}]}

            if interview.coding_info:
                data["sections"][0]["facts"].append(
                    {"name": f"Coding Info",
                     "value": interview.coding_info
                     },
                )
            post_msg_using_webhook(config.engineering_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def coder_assigned_card(interview, request):
        try:
            profile_path = get_profile_picture(request.user)
            coding_experts = ", ".join(interview.guest.all().values_list('employee_name', flat=True))
            data = {
                "@type": "MessageCard",
                "themeColor": "#0076D7",
                "@context": "http://schema.org/extensions",
                "summary": f"Coding expert request for Interview ",
                "sections": [
                    {
                        "activityTitle": "Coding assignment",
                        "activitySubtitle": f"I-{interview.id} : Interview from ***{interview.submission.client}*** for "
                                            f" ***{interview.submission.consultant.name}*** ",
                        "activityText": f"Requested by ***{interview.submission.created_by.employee_name}*** from "
                                        f"***{interview.submission.created_by.team.name}***",
                        "activityImage": profile_path,
                        "facts": [
                            {
                                "name": "Technology",
                                "value": str(interview.tech_stack)
                            },
                            {
                                "name": "Supervisor",
                                "value": str(interview.supervisor.employee_name)
                            },
                            {
                                "name": "Date",
                                "value": str(interview.start_time.strftime('%a, %d %B'))
                            },
                            {
                                "name": "Time",
                                "value": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                         f"{interview.end_time.strftime('%I:%M %p EST')}"
                            },
                            {
                                "name": "Coding Expert",
                                "value": coding_experts
                            }
                        ],
                        "markdown": True
                    }
                ]
            }
            post_msg_using_webhook(config.engineering_url, data)
            return 'ok'
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def test_received_card(payload, request):
        try:
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",
                "themeColor": "#0076D7",
                "@context": "http://schema.org/extensions",
                "summary": f"Coding expert request for Interview ",
                "sections": [
                    {
                        "activitySubtitle": payload.get('subtitle', 'NA'),
                        "activityImage": profile_path,
                        "activityText": payload.get('activity_text', 'NA'),
                        "activityTitle": "Test Received",
                        "facts": [
                            {
                                "name": "Timezone",
                                "value": payload.get('timezone', 'NA')
                            },
                            {
                                "name": "Deadline",
                                "value": payload.get('deadline', 'NA')
                            }
                        ],
                        "markdown": True
                    }
                ]
            }
            post_msg_using_webhook(config.engineering_url, data)
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
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "#0076D7",
                "summary": "Project Joined",
                "sections": [{
                    "activityTitle": "Project Joined",
                    "activitySubtitle": payload.get('activity_text', 'NA'),
                    "activityText": payload.get('activity_title', 'NA'),
                    "activityImage": profile_path,
                    "facts": [
                        {
                            "name": f"Submitted On",
                            "value": payload.get('submitted_on', 'NA')
                        },
                        {
                            "name": f"Employer",
                            "value": payload.get('employer', 'NA')
                        },
                        {
                            "name": f"Recruiter",
                            "value": payload.get('recruiter_name', 'NA')
                        }
                    ],
                    "markdown": True
                }],
                "potentialAction": [{
                    "@type": "ActionCard",
                    "name": f"{payload.get('team_name', 'NA')} - {payload.get('team', 'NA')}",
                    "actions": [{
                        "@type": "HttpPOST",
                        "name": f"{payload.get('team_name', 'NA')} - {payload.get('team', 'NA')}",
                        "target": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                    }]
                }, {
                    "@type": "ActionCard",
                    "name": f"Total - {payload.get('total', 'NA')}",
                    "actions": [{
                        "@type": "HttpPOST",
                        "name": f"Total - {payload.get('total', 'NA')}",
                        "target": f"https://app.log1.com/api/util/?api_key={os.environ.get('teams_api_key')}"
                    }]
                }, {
                    "@context": "http://schema.org",
                    "@type": "ViewAction",
                    "name": "View in Log1",
                    "target": [
                        f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}"
                    ]
                }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.joined_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_termination_message_card(payload, request):
        try:
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "#0076D7",
                "summary": "Project Termination",
                "sections": [{
                    "activityTitle": "Project Termination Feedback",
                    "activitySubtitle": payload.get('activity_sub_title', ''),
                    "activityText": payload.get('activity_text', ''),
                    "activityImage": profile_path,
                    "facts": [
                        {"name": f"Project duration", "value": f"{payload.get('months', 0)} months"},
                        {"name": f"Employer", "value": payload.get('employer', "NA")},
                        {"name": f"Location", "value": payload.get('project.city', "NA")},
                        {"name": f"Recruiter", "value": payload.get('recruiter_name', "NA")},
                        {"name": f"Status", "value": payload.get('status', "NA")},
                        {"name": f"Feedback", "value": payload.get('reason', "NA")},
                    ],
                    "markdown": True
                }],
                "potentialAction": [{
                    "@context": "http://schema.org",
                    "@type": "ViewAction",
                    "name": "View in Log1",
                    "target": [
                        f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}"
                    ]
                }]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.project_termination_url, data)

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
            post_msg_using_webhook(config.offer_url, data)
            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)

    @staticmethod
    def po_cancellation_message_card(payload, request):
        try:
            profile_path = get_profile_picture(request.user)
            data = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "#0076D7",
                "summary": "Project Joined",
                "sections": [{
                    "activityTitle": "Offer Cancellation Feedback",
                    "activitySubtitle": payload.get('activity_sub_title', ''),
                    "activityText": payload.get('activity_text', ''),
                    "activityImage": profile_path,
                    "facts": [
                        {"name": f"Employer", "value": payload.get('employer', 'NA')},
                        {"name": f"Location", "value": payload.get('city', 'NA')},
                        {"name": f"Recruiter", "value": payload.get('recruiter_name', 'NA')},
                        {"name": f"Status", "value": payload.get('status', 'NA')},
                        {"name": f"Feedback", "value": payload.get('reason', 'NA')},
                    ],
                    "markdown": True
                }],
                "potentialAction": [
                    {
                        "@context": "http://schema.org",
                        "@type": "ViewAction",
                        "name": "View in Log1",
                        "target": [
                            f"https://app.log1.com/#/details/{payload.get('submission_id')}/project?id={payload.get('project_id')}"
                        ]
                    }
                ]
            }
            # Sending message on Messaging Tool
            post_msg_using_webhook(config.offer_failure_url, data)

            return "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error)
