from constance import config
from django.core.management import BaseCommand

from log1.utils import post_msg_using_webhook
from project.models import ConsultantFeedback
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Submission report"

    def handle(self, *args, **options):
        job = create_cron_object(name='marketer_submission')
        try:
            feedbacks = ConsultantFeedback.objects.filter(
                feedback_type='engineering_issue', created__gte="2022-04-01", created__lt="2022-07-01"
            )
            for feedback in feedbacks:
                project = feedback.project
                if project.submission:
                    text = f":: {project.submission.lead.job_title} ::" if project.submission.lead else "::"
                    title = f"*{project.consultant.name} {text} {project.submission.client}*"
                else:
                    title = project.consultant.name
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
                    post_msg_using_webhook(config.candidate_feedback_url, data)

        except Exception as error:
            create_cron_error(job, error)
