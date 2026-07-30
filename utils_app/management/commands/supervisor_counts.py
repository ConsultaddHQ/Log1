import csv
from datetime import date, datetime, timedelta
from django.core.management import BaseCommand

from employee.models import User
from marketing.models import Interview

START_GT = "2023-12-31"
START_LT = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            import csv
            file = open("SupervisorCounts.csv", "w")
            writer = csv.writer(file)
            interview_qs = Interview.objects.filter(start_time__gt=START_GT, start_time__lt=START_LT, screening_type='interview').exclude(status__in=['cancelled', 'scheduled', 'rescheduled'])
            supervisors = interview_qs.order_by('supervisor_id').distinct('supervisor_id').values_list('supervisor', flat=True)
            MAX_ROUND = interview_qs.order_by('-round').first().round
            columns = ["Employee Name", "Total Interview Count"]
            for _round in range(1, MAX_ROUND+1):
                columns.extend([
                    f"R-{_round} Total", f"R-{_round} Passed", f"R-{_round} Failed",
                    f"R-{_round} FeedbackDue", f"R-{_round} OtterAI", f"R-{_round} Supervisor",
                ])
            writer.writerow(columns)
            for sup in supervisors:
                user = User.objects.get(id=int(sup))
                row_data = list()
                row_data.append(user.employee_name)
                total_int_qs = interview_qs.filter(supervisor=user)
                row_data.append(total_int_qs.count())
                for _round in range(1, MAX_ROUND + 1):
                    _round_qs = total_int_qs.filter(round=_round)
                    total = _round_qs.count()
                    passed = _round_qs.filter(status__in=['passed', 'next_round']).count()
                    failed = _round_qs.filter(status__in=['failed']).count()
                    feedback_due = _round_qs.filter(status__in=['feedback_due']).count()
                    supervisor = _round_qs.filter(call_type__display_name='Supervisor').count()
                    otter_ai = _round_qs.filter(call_type__display_name='Otter AI').count()
                    row_data.extend([total, passed, failed, feedback_due, supervisor, otter_ai])
                writer.writerow(row_data)
        except Exception as error:
            print(error)
