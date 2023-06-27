from django.db.models import Q
from datetime import timedelta, date, timezone
from django.core.management import BaseCommand

from django.utils import timezone
from project.models import ProjectSupport
from utils_app.utils import create_cron_error, create_cron_object
from notification.utils import create_notification, push_notification


class Command(BaseCommand):
    help = "This command is send the push notification to project support person if it's project consultant feedback is due form last 30 days"

    def handle(self, *args, **options):
        job = create_cron_object('feedback_push_notification')
        try:
            today = date.today()
            thirty_days_ago = today - timedelta(days=30)

            # Query to fetch the project support instances
            breakpoint()
            project_support_persons = ProjectSupport.objects.filter(
                ~Q(project__feedbacks__created__gte=thirty_days_ago) &
                Q(project__support_required=True,statuses__frequency__in=['is_active','less_active'])
            )
            for support_person in project_support_persons:
                data = {
                    "title": "consultant feedback due",
                    "category": "alert",
                    "description": f"your {support_person.project.consultant.name} feedback were not given form last 30 days",
                    "target_type": "log1",
                    "target_id": support_person.support.id,
                    "sender_id": support_person.support.id,
                    "recipient_user_type": "user",
                    "sender_user_type": "user",
                }

                create_notification([support_person.support.id], data)

                # Push Notification
                message_body = {
                    "body": f"your {support_person.project.consultant.name} updates were not given for last weeks",
                    "title":"project update due",
                    "category": "alert",
                    "show_in_foreground": True,
                    "click_action": "https://app.log1.com/#/engineering_module",
                    "data": {
                        'is_read': False,
                        'is_deleted': False,
                        'target': 'log1',
                        'target_id':support_person.support.id,
                        'timestamp': str(timezone.now()),
                    },
                }
                push_notification([support_person.support.id], message_body)

        except Exception as error:
            create_cron_error(job, error)