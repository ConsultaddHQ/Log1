from django.utils import timezone
from datetime import date, timedelta
from django.core.management import BaseCommand
from django.contrib.contenttypes.models import ContentType

from project.models import TimeSheet
from notification.models import Notification, FCMDevice
from notification.utils import push_notification_consultant
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        job = create_cron_object(name='monday_ts_reminder')
        try:
            queryset = TimeSheet.objects.filter(
                is_active=True, status='draft', end=date.today() - timedelta(days=2),
                project__statuses__status='joined', project__statuses__is_current=True
            ).order_by('project__consultant__id').distinct('project__consultant_id')
            for timesheet in queryset:
                consultant = timesheet.project.consultant
                title = f"Reminder: Please submit timesheet for the week {str(timesheet.start.strftime('%m/%d/%Y'))} - " \
                        f"{str(timesheet.end.strftime('%m/%d/%Y'))}"
                message_body = {
                    "body": None,
                    "title": title,
                    "category": "pending",
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
                    description=title,
                    category="pending",
                    sender_object_id=1,
                    target_object_id=timesheet.id,
                    recipient_object_id=consultant.id,
                    sender_content_type=sender_content_type,
                    target_content_type=target_content_type,
                    recipient_content_type=recipient_content_type,
                )
                tokens = list(consultant.consultant_token.all().values_list('key', flat=True))
                device_ids = list(FCMDevice.objects.filter(object_id__in=tokens).values_list('device_id', flat=True))
                push_notification_consultant(device_ids, message_body)
        except Exception as error:
            create_cron_error(job, error)
