from django.db.models import Q,F
from django.utils import timezone
from datetime import timedelta, date
from django.core.management import BaseCommand


from project.models import ProjectSupport
from employee.models import User
from notification.models import UserNotification
from django.contrib.auth.models import ContentType
from utils_app.utils import create_cron_error, create_cron_object
from notification.utils import create_notification, push_notification


class Command(BaseCommand):
    help = "This command is send the push notification to project support person if it's project consultant feedback is due form last 30 days"

    def handle(self, *args, **options):
        job = create_cron_object('feedback_push_notification')
        try:
            today = date.today()
            thirty_days_ago = today - timedelta(days=30)
            fourteen_days_ago = today - timedelta(days=14)

            # Query to fetch the project support instances
            active_projects = ~Q(project__feedbacks__created__gte=thirty_days_ago,
                                 project__feedbacks__feedback_type__in=["independent", "2_week",
                                                                        "engineering_issue"]) & Q(
                project__start_date__lte=thirty_days_ago
            )

            initial_projects = ~Q(project__feedbacks__created__gte=fourteen_days_ago,
                                  project__feedbacks__feedback_type__in=['independent', '2_week',
                                                                         'engineering_issue']) & Q(
                project__start_date__gte=thirty_days_ago, project__start_date__lte=fourteen_days_ago)

            project_support_persons = ProjectSupport.objects.filter(
                Q(end__isnull=True, project__support_required=True, is_proxy_support=False,
                  statuses__is_current=True, statuses__frequency__in=['active', 'less_active'], ) &
                (active_projects | initial_projects)).order_by('project__id').distinct('project__id')

            content_type = ContentType.objects.get(model='consultant')
            for support_person in project_support_persons:
                notification, created = UserNotification.objects.get_or_create(user=User.objects.get(id=support_person.support.id),
                                                                               content_type=content_type)
                if created:
                    notification.is_active = True
                    notification.save()
                data = {
                    "title": "consultant feedback due",
                    "category": "alert",
                    "target_type": "feedback",
                    "sender_user_type": "user",
                    "recipient_user_type": "user",
                    "sender_id": support_person.support.id,
                    "target_id": support_person.project.consultant.id,
                    "description":
                        f"your {support_person.project.consultant.name} feedback were not given form last 30 days"
                }

                create_notification([support_person.support], data)

                # Push Notification
                message_body = {
                    "body": f"your {support_person.project.consultant.name} feedback were not given form last 30 days",
                    "title":"project update due",
                    "category": "alert",
                    "show_in_foreground": True,
                    "click_action": "https://app.log1.com/#/engineering_module",
                    "data": {
                        'target': 'log1',
                        'is_read': False,
                        'is_deleted': False,
                        'timestamp': str(timezone.now()),
                        'target_id': support_person.project.consultant.id
                    },
                }
                push_notification([support_person.support.id], message_body)

        except Exception as error:
            create_cron_error(job, error)