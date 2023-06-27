from django.db.models import Q
from datetime import timedelta, date
from django.core.management import BaseCommand

from django.utils import timezone
from project.models import ProjectSupport
from utils_app.utils import create_cron_error, create_cron_object
from notification.utils import  create_notification, push_notification


class Command(BaseCommand):
    help = "This command send the push notification to project support person if project updates are pending form last 7 days "

    def handle(self, *args, **options):
        job = create_cron_object('support_push_notification')
        try:
            today = date.today()
            start_of_last_week = today - timedelta(days=today.weekday(), weeks=1)
            end_of_last_week = start_of_last_week + timedelta(days=6)

            seven_days_ago = today - timedelta(days=7)

            # Query to fetch the project support person

            # use case notification send on 14 days if user submit the feedback on monday script run on monday
            project_support_persons = ProjectSupport.objects.filter(
                ~Q(project__updates__start__range=(start_of_last_week, end_of_last_week)) &
                Q(project__support_required=True)
            )

            # user case send the notification to user on daily base if can not submit the feedback script run daily
            project_support_persons = ProjectSupport.objects.filter(
                ~Q(project__updates__created__gte=seven_days_ago) &
                Q(project__support_required=True,statuses__frequency__in=['is_active','less_active'])
            )

            for support_person in project_support_persons:
                data = {
                    "title": "project update due",
                    "category": "alert",
                    "description": f"your {support_person.project.consultant.name} updates were not given for last weeks",
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
                    "click_action": f"https://app.log1.com/#/project/{support_person.project.id}/project_update",
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