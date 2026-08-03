import csv

from django.core.management import BaseCommand

from marketing.models import Interview


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            file = open("submission_report.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Sub ID", "Consultant Name", "Client", "Vendor", "Project Type", "Rate", "Marketer Name",
                "Marketing Team", "Job Title", "Employer", "Created Date", "Status", "Total Rounds", "Current Status"
            ])
            int_qs = Interview.objects.exclude(
                status__in=['cancelled']
            ).filter(screening_type='interview', created__gt="2024-07-31").order_by('submission_id').distinct('submission_id')
            for obj in int_qs:
                status = None
                sub = obj.submission
                if int_qs.filter(submission=sub, status='offer').first():
                    status = f"offer"
                if not status:
                    failed_interview = int_qs.filter(submission=sub, status='failed').first()
                    if failed_interview:
                        status = f"Failed - {', '.join(failed_interview.failure_reason)}"
                    else:
                        status = "In Process"
                sub_int_qs = Interview.objects.filter(
                    screening_type='interview', submission=sub, created__gt="2024-07-31"
                ).exclude(status__in=['cancelled']).order_by('-id')

                writer.writerow([
                    sub.id, sub.consultant.name, sub.client, sub.vendor.name, sub.get_work_type_display(),
                    sub.rate, sub.created_by.employee_name, sub.marketing_team.name, sub.lead.job_title,
                    sub.employer, sub.created.date(), status, sub_int_qs.count(), sub_int_qs.order_by('-id').first().get_status_display()
                ])
        except Exception as e:
            print(str(e))
