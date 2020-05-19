from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from datetime import date, timedelta
from project.models import TimeSheet
from notification.views import push_notification
from notification.models import Notification, FCMDevice


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        timesheets = TimeSheet.objects.filter(status='draft', end__lte=date.today() - timedelta(days=2))
        for timesheet in timesheets:
            consultant = timesheet.project.consultant
            title = f"Reminder: Please submit timesheet for the week {str(timesheet.start)} - {str(timesheet.end)}"
            message_body = {
                "body": title,
                "title": None,
                "category": "info",
                "show_in_foreground": True,
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'timesheet',
                    'target_id': timesheet.id,
                    'timestamp': str(timezone.now()),
                },
            }

            recipient_content_type = ContentType.objects.get(model="consultant")
            sender_content_type = ContentType.objects.get(model="user")
            target_content_type = ContentType.objects.get(model="timesheet")
            Notification.objects.create(
                title=title,
                category="info",
                description=title,
                sender_object_id=1,
                target_object_id=timesheet.id,
                recipient_object_id=consultant.id,
                sender_content_type=sender_content_type,
                target_content_type=target_content_type,
                recipient_content_type=recipient_content_type,
            )
            tokens = list(consultant.consultant_token.all().values_list('key', flat=True))
            device_ids = list(FCMDevice.objects.filter(object_id__in=tokens).values_list('device_id', flat=True))
            result = push_notification(device_ids, message_body)
            break
