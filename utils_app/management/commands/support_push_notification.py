from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta, date
from django.core.management import BaseCommand

from notification.models import UserNotification
from employee.models import User
from django.contrib.auth.models import ContentType
from project.models import ProjectSupport
from utils_app.utils import create_cron_error, create_cron_object
from notification.utils import  create_notification, push_notification


class Command(BaseCommand):
    help = "This command send the push notification to project support person if project updates are pending form last 7 days "

    def handle(self, *args, **options):
        job = create_cron_object('support_push_notification')
        try:
            today = date.today()
            # start_of_last_week = today - timedelta(days=today.weekday(), weeks=1)
            # end_of_last_week = start_of_last_week + timedelta(days=6)
            seven_days_ago = today - timedelta(days=7)
            one_day_ago = today - timedelta(days=1)

            # Query to fetch the project support person
            # user case send the notification to user on daily base if can not submit the feedback script run daily
            active_projects = Q(~Q(project__updates__created__gte=seven_days_ago), start__lte=seven_days_ago,
                                statuses__created__lte=seven_days_ago,
                                statuses__frequency__in=['active', 'less_active'])

            training_projects = Q(~Q(project__updates__created__gte=one_day_ago),
                                  project__start_date__gte=date.today())

            project_support_persons = ProjectSupport.objects.filter(
                Q(end__isnull=True,is_proxy_support=False, statuses__is_current=True,
                  project__support_required=True) & (
                        active_projects | training_projects)).order_by('project__id').distinct('project__id')

            content_type = ContentType.objects.get(model='project')

            for support_person in project_support_persons:
                notification, created = UserNotification.objects.get_or_create(
                    user=User.objects.get(id=support_person.support.id), content_type=content_type
                )
                if created:
                    notification.is_active = True
                    notification.save()

                data = {
                    "title": "project update due",
                    "category": "alert",
                    "description": f"your {support_person.project.consultant.name} updates were not given for last weeks",
                    "target_type": "projectupdate",
                    "target_id": support_person.project.id,
                    "sender_id": support_person.support.id,
                    "recipient_user_type": "user",
                    "sender_user_type": "user",
                }
                create_notification([support_person.support], data)

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
                        'target_id': support_person.project.id,
                        'timestamp': str(timezone.now()),
                    },
                }
                push_notification([support_person.support.id], message_body)

        except Exception as error:
            create_cron_error(job, error)