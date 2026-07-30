import csv
from django.core.management import BaseCommand

from project.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        file = open("PayrollConsultant.csv", 'w+')
        writer = csv.writer(file)
        writer.writerow([
            "Consultant Name", "Email", "Phone Number", "Client", "Payroll Employer", "Project Start Date",
            "Project End Date", "Consultant Joining Date", "Consultant Exit Date", "Consultant Exit Reason",
            "Consultant Status", "Internal Employee"
        ])
        project_qs = Project.objects.filter(statuses__status='joined').order_by('id').distinct('id')

        for obj in project_qs:
            consultant = obj.submission.consultant
            consultant_exit = consultant.exit.filter().order_by('-id').first()
            exit_date = None
            exit_reason = None
            if consultant_exit:
                exit_date = consultant_exit.resign_date if consultant_exit.resign_date else consultant_exit.last_date \
                    if consultant_exit.last_date else consultant_exit.created.strftime("%Y-%m-%d")
                exit_reason = " ,".join(consultant_exit.reasons.all().values_list('name', flat=True))

            payroll_employer = 'Consultadd'
            if obj.employer:
                payroll_employer = obj.employer
            writer.writerow([
                consultant.name, consultant.email, consultant.phone_no, obj.submission.client, payroll_employer, obj.start_date, obj.end_date,
                consultant.created.strftime("%Y-%m-%d"), exit_date, exit_reason, consultant.get_status_display(), "Yes" if consultant.internal_user_profile else "No"
            ])