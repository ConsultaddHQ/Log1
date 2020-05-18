from datetime import date
from django.core.management import BaseCommand
from django.utils import timezone

from constance import config
from employee.models import User
from consultant.models import Terminate
from notification.models import FCMDevice
from utils_app.utils import post_msg_using_webhook, html_to_text
from notification.views import push_notification, create_notification


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        queryset = Terminate.objects.filter(last_date__lte=date.today(), is_complete=False)
        for terminate in queryset:
            consultant = terminate.consultant
            consultant.status = 'terminated'
            consultant.save()

            marketings = consultant.marketing.filter(status='open')
            for marketing in marketings:
                marketing.status = 'close'
                marketing.end = date.today()
                marketing.save()

            terminate.is_complete = True
            terminate.save()

            # Mattermost message for Exit Interview
            exit_details = html_to_text(terminate.exit_details)
            text = f"#### Exit interview for {consultant.name}\n" \
                   f"**Reason for leaving** : {terminate.reason.upper()}\n" \
                   f"**Termination Date** : {terminate.last_date}\n" \
                   f"**Exit Interview Details** : {exit_details} \n"

            data = {
                "response_type": "in_channel",
                "username": "Log1 Updates",
                "text": text,
            }
            post_msg_using_webhook(config.exit_interview_url, data)

            # App Notification
            recruiter = consultant.recruiter
            user_list = [recruiter]
            scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
            for user in scrum_masters:
                user_list.append(user)

            notification_data = {
                'category': 'info',
                'sender_user_type': 'user',
                'target_type': 'consultant',
                'recipient_user_type': 'user',
                'description': terminate.reason,
                'title': 'Consultant Termination',
                'sender_id': terminate.created_by.id,
                'target_id': terminate.consultant.id,
            }
            create_notification(user_list, notification_data)

            # Push Notification
            message_body = {
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "body": f"{consultant.name} got terminated today",
                "title": f"{consultant.name} got terminated today",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'timestamp': str(timezone.now()),
                    'target_id': terminate.consultant.id,
                },
            }

            object_ids = []
            for user in user_list:
                object_ids.append(user.id)

            registration_ids = list(
                FCMDevice.objects.filter(object_id__in=list(object_ids), content_type__model='user'
                                         ).values_list('device_id', flat=True))
            push_notification(registration_ids, message_body)
