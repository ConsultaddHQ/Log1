import csv
from datetime import date, timedelta, datetime

from constance import config
from django.core.management import BaseCommand

from employee.models import User
from project.models import Project


class Command(BaseCommand):

    @staticmethod
    def get_supervisor(po):
        interviews = po.submission.screening.all().values_list("supervisor__employee_name", flat=True)
        return ", ".join(interviews)

    @staticmethod
    def get_coder(po):
        coder = []
        for int in po.submission.screening.all():
            if int.coding_present:
                for guest in int.guests.filter(type__in=['Assigned Coder & Assistance', 'Assigned Coder', 'Coder']):
                    coder.append(guest.user.employee_name)
        return ", ".join(set(coder))

    def handle(self, *args, **options):
        try:
            file = open("offer_received.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Project ID", "Client", "Consultant Name", "Project Start Date", "Project Received Date",
                "Project Joined Date", "Duration", "Marketer Name", "Marketer EmpID", "Recruiter Name",
                "Recruiter EmpID", "Supervisor", "Coder", "Support", "VP", "Team Lead", "Lead SM", "Current Status", "APP URL"
            ])
            projects = Project.objects.filter(
                statuses__status='received', statuses__created__gt='2023-10-31', statuses__created__lt='2024-02-01'
            )
            for po in projects:
                Support = ", ".join(support.support.employee_name for support in po.support.all())
                received_date = po.statuses.filter(status='received').first()

                joined_date = po.statuses.filter(status='joined').first()
                joined_date = joined_date.created.date() if joined_date else "Not Joined"
                tl = User.objects.filter(team=po.submission.marketing_team, role__name='admin').first()
                tl_ = tl.employee_name if tl else "NA"
                if po.submission.marketing_team.name == "Consultadd Canada":
                    vp = "Arpit Mehta"
                    lm = "Not Required"
                else:
                    vp = "Arun Kumar"
                    lm = "Vinal Khelani"
                if po.submission.consultant.recruiter:
                    recruiter_id = po.submission.consultant.recruiter.employee_id
                    recruiter_name = po.submission.consultant.recruiter.employee_name
                else:
                    recruiter_id = "NA"
                    recruiter_name = "Not Assigned"

                writer.writerow([
                    po.id, po.submission.client, po.submission.consultant.name, po.start_date,
                    received_date.created.date().strftime("%Y-%m-%d"), joined_date,
                    "0 days", po.submission.created_by.employee_name,
                    po.submission.created_by.employee_id, recruiter_name, recruiter_id, self.get_supervisor(po),
                    self.get_coder(po), Support, vp, tl_, lm, po.status,
                    f"{config.APP_URL}#/details/{po.submission_id}/project?id={po.id}"
                ])
        except Exception as error:
            breakpoint()
            print(error)
