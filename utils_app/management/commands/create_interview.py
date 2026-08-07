from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from activity.models import Activity
from employee.models import User
from marketing.models import Interview, Submission
from utils_app.models import Choice


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            start_datetime_str = '03/11/24 15:00:00'
            end_datetime_str = '03/11/24 16:00:00'
            submission = Submission.objects.get(id=92102)
            supervisor = User.objects.get(employee_id=2602)
            interview = Interview.objects.create(
                submission=submission, supervisor=supervisor, status='feedback_due', round=2,
                coding_present=False, assistance_required=False, guest_type='Not Required',
                start_time=datetime.strptime(start_datetime_str, '%m/%d/%y %H:%M:%S'),
                end_time=datetime.strptime(end_datetime_str, '%m/%d/%y %H:%M:%S'),
                interview_mode='video_call', screening_type='interview',
                call_type=Choice.objects.get(name='supervisor'),
                created=datetime.strptime(start_datetime_str, '%m/%d/%y %H:%M:%S')
            )
            end = interview.end_time.strftime("%Y-%m-%d %H-%M")
            start = interview.start_time.strftime("%Y-%m-%d %H-%M")
            desc = f"Interview round {interview.round} is scheduled for " \
                   f"{start.split(' ')[0]}-{start.split(' ')[1]} to {end.split(' ')[0]}-{end.split(' ')[1]}"

            Activity.objects.create(
                desc=desc,
                object_id=submission.id,
                activity_type='created',
                user=User.objects.get(employee_id=10087),
                content_type=ContentType.objects.get(model='submission'),
                created=datetime.strptime(start_datetime_str, '%m/%d/%y %H:%M:%S'),
            )
        except Exception as e:
            print(str(e))
