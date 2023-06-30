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
            project_support_persons = ProjectSupport.objects.filter(
                (~Q(project__feedbacks__created__gte=thirty_days_ago)|Q(project__feedbacks__created__gte=fourteen_days_ago,project__created__lte=thirty_days_ago))&
                Q(project__support_required=True,statuses__frequency__in=['is_active','less_active'])
            )
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
                    "body": f"your {support_person.project.consultant.name} feedback were not given form last 30 days",
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