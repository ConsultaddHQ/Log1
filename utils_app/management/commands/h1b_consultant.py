import csv
from django.core.management import BaseCommand

from consultant.models import Consultant
from project.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        file = open("h1b_consultant.csv", "w+")
        writer = csv.writer(file)
        writer.writerow([
            "Consultant Name", "Consultant Email", "Consultant Phone Number", "Client",
            "Payroll Employer", "Project Status", "Project Start Date", "Project End Date", "Consultant Joining Date",
            "Consultant Exit Date", "Current City", "Visa Start Date", "Visa End Date", "Consultant Status",
            "Consultant Exit Status", "Consultant Exit Reason", "Internal User"
        ])

        queryset = Project.objects.filter(
            submission__consultant_marketing__consultant__work_auth__visa_type='h1b',
            submission__consultant_marketing__consultant__work_auth__is_current=True
        )
        for obj in queryset:
            consultant = obj.submission.consultant
            consultant_exit = consultant.exit.filter().order_by('-id').first()
            exit_date = None
            exit_status = None
            exit_reason = None
            if consultant_exit:
                exit_date = consultant_exit.resign_date if consultant_exit.resign_date else consultant_exit.last_date \
                    if consultant_exit.last_date else consultant_exit.created.strftime("%Y-%m-%d")
                exit_status = consultant_exit.get_status_display()
                exit_reason = " ,".join(consultant_exit.reasons.all().values_list('name', flat=True))
            visa_status = consultant.work_auth.filter(is_current=True).first()
            visa_start_date = visa_status.visa_start
            visa_end_date = visa_status.visa_end

            payroll_employer = 'Consultadd'
            if obj.employer:
                payroll_employer = obj.employer
            writer.writerow([
                consultant.name, consultant.email, consultant.phone_no, obj.submission.client,
                payroll_employer, obj.status, obj.start_date, obj.end_date, consultant.created.strftime("%Y-%m-%d"),
                exit_date, consultant.current_city, visa_start_date, visa_end_date, consultant.get_status_display(),
                exit_status, exit_reason, "Yes" if consultant.internal_user_profile else "No"
            ])
