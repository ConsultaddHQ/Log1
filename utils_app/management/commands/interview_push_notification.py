import os

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from pytz import timezone
from datetime import timedelta, date, datetime
from django.core.management import BaseCommand

from employee.models import User
from log1.utils import write_exception
from marketing.models import Interview
from notification.models import FCMDevice, UserNotification
from notification.utils import create_notification, push_notification_consultant


class Command(BaseCommand):

    @shared_task()
    def delete_supervisor_notification(self):
        try:
            content_type = ContentType.objects.get(model='interview')
            notifications = UserNotification.objects.filter(content_type=content_type)
            for notification in notifications:
                interviews = Interview.objects.filter(status="feedback_due", supervisor=notification.user)
                if not interviews:
                    notification.delete()
        except Exception as error:
            write_exception(error, None)
            return str(error), False
    def handle(self, *args, **options):
        try:
            # breakpoint()
            """
                Updates the status of interviews and sends push notifications for feedback.

                - Retrieves interviews that have a start time earlier than or equal to the current UTC time
                  and have a status of 'scheduled' or 'rescheduled'.
                - Updates the status of the retrieved interviews to 'feedback_due'.
                - Deletes push notifications for which there are no corresponding interviews with 'feedback_due' status.
                - Creates push notifications for supervisors associated with screenings in 'feedback_due' status.
                - Sends push notifications to supervisors with the necessary information.
                """
            tz = timezone('US/Eastern')
            time_est = datetime.now(tz).replace(tzinfo=timezone('UTC'))
            previous_interviews = Interview.objects.filter(
                start_time__lte=time_est, status__in=['scheduled', 'rescheduled']
            )
            for interview in previous_interviews:
                interview.status = 'feedback_due'
                interview.save()

            # Deletes push notifications for which there are no corresponding interviews with 'feedback_due' status.
            if os.environ.get('ENV') == 'prod':
                self.delete_supervisor_notification.delay()

            # Creates push notifications for supervisors associated with screenings in 'feedback_due' status.
            interviews = Interview.objects.filter(
                start_time__gte=datetime.strptime("2022-05-04", "%Y-%m-%d"),
                end_time__lte=datetime.now(timezone('US/Eastern')).replace(tzinfo=timezone('UTC')) - timedelta(
                    hours=4)
            ).exclude(
                status__in=["cancelled", "next_round", "offer", "failed", "scheduled", "rescheduled"]
            ).exclude(
                supervisor_feedback__question__form_name='interview'
            ).order_by('id').distinct('id')
            print(interviews)
            supervisor_ids = interviews.values_list('supervisor', flat=True).distinct()
            supervisor_list = User.objects.filter(id__in=supervisor_ids)
            for interview in interviews:
                content_type = ContentType.objects.get(model='interview')
                notification, created = UserNotification.objects.get_or_create(user=interview.supervisor,
                                                                               content_type=content_type)
                if created:
                    notification.is_active = True
                    notification.save()
                    message_body = {
                        "body": "interview feedback due", "title": "interview feedback due", "category": "PopUp",
                        "data": {
                            'supervisor_id': interview.supervisor.id,
                            'count': 1
                        },
                    }
                    data = {
                        "title": "interview feedback due",
                        "category": "alert",
                        "description": f"your {interview.submission.consultant_marketing.consultant.name} interview (I-{interview.id}) supervisor feedback is pending",
                        "parent_type": "submission",
                        "target_type": "interview",
                        "parent_id": interview.submission.id,
                        "target_id": interview.id,
                        "sender_id": interview.supervisor.id,
                        "recipient_user_type": "user",
                        "sender_user_type": "user",
                    }
                    create_notification([interview.supervisor.id], data)
                    registration_ids = list(
                        FCMDevice.objects.filter(
                            object_id=interview.supervisor.id, content_type__model='user').values_list('device_id',
                                                                                                       flat=True))
                    push_notification_consultant(registration_ids, message_body)

        except Exception as error:
            write_exception(message=error)
            return None