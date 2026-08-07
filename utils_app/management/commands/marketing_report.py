import csv

from django.core.management import BaseCommand

from employee.models import User
from project.models import Project
from marketing.models import Submission, Interview


class Command(BaseCommand):
    def handle(self, *args, **options):
        count = 0
        try:
            file = open("Marketing.csv", "r")
            write_file = open("MarketingReport.csv", "w+")
            reader = csv.reader(file)
            writer = csv.writer(write_file)
            for row in reader:
                if count == 0:
                    count += 1
                    writer.writerow([
                        'Employee Number', 'Employee Name', 'Designation', 'Department',
                        'Current Experience (year/ Month)', 'Submission', 'Interviews', 'Offer', 'Last offer month'
                    ])
                    continue

                user_obj = User.objects.filter(employee_id=int(row[0])).first()
                if not user_obj:
                    user_obj = User.objects.filter(employee_name__istartswith=row[1]).first()
                    if not user_obj:
                        writer.writerow([row[0], row[1], row[2], row[3], row[4]])
                        continue

                submission_qs = Submission.objects.filter(
                    created_by=user_obj
                )
                interview = Interview.objects.filter(
                    submission__created_by=user_obj
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id')
                offers = Project.objects.filter(
                    
                    statuses__status__in=['new', 'received', 'on_boarded'], submission__created_by=user_obj
                ).order_by('-id').distinct('id')
                latest_offer = f"{offers.first().created.strftime('%B - %y')}"\
                    if offers.first() else "Not Received yet"

                writer.writerow([
                    row[0], row[1], row[2], row[3], row[4], submission_qs.count(), interview.count(), offers.count(),
                    latest_offer
                ])

        except Exception as error:
            print(error)
