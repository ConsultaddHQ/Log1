from datetime import date, datetime
from django.core.management import BaseCommand
from django.utils import timezone

from employee.models import User
from notification.models import FCMDevice
from consultant.models import ConsultantExit
from consultant.views import send_exit_process_mail
from notification.views import push_notification, create_notification


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        queryset = ConsultantExit.objects.filter(last_date__lte=date.today(), status='in_process')
        for terminate in queryset:
            consultant = terminate.consultant
            consultant.status = 'terminated'
            consultant.save()

            marketings = consultant.marketing.filter(status='open')
            for marketing in marketings:
                marketing.status = 'close'
                marketing.end = date.today()
                marketing.save()

            terminate.status = 'complete'
            terminate.save()

            # Email for Exit Process Cancelled
            send_exit_process_mail(terminate, 'complete')

            # App Notification
            recruiter = consultant.recruiter
            user_list = [recruiter]
            scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
            for user in scrum_masters:
                user_list.append(user)

            last_date = datetime.strptime(terminate.last_date, "%Y-%m-%d").strftime("%b. %d, %Y")
            title = f"""{consultant.name} got terminated on {last_date}"""

            notification_data = {
                'category': 'info',
                'sender_user_type': 'user',
                'target_type': 'consultant',
                'recipient_user_type': 'user',
                'description': terminate.type,
                'title': title,
                'sender_id': terminate.created_by.id,
                'target_id': terminate.consultant.id,
            }
            create_notification(user_list, notification_data)

            # Push Notification
            message_body = {
                "body": None,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'timestamp': str(timezone.now().strftime('%m/%d/%Y')),
                    'target_id': terminate.consultant.id,
                },
            }

            object_ids = []
            for user in user_list:
                object_ids.append(user.id)
            push_notification(object_ids, message_body)
