import csv

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from project.models import ConsultantLeave
from utils_app.models import Choice
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_consultant_leave')
        try:
            assigned, already = 0, 0
            content_type = ContentType.objects.get(model='consultantleave')
            # leave_types = {
            #     'Sick leave': 'sick_leave',
            #     'PTO': 'pto',
            #     'Maternity': 'maternity',
            #     'Paternity': 'paternity',
            #     'Marriage leave': 'marriage_leave',
            #     'Covid emergency sick leave': 'covid_emergency_sick_leave'
            # }
            # for items in leave_types.items():
            #     choice = Choice.objects.get(
            #         name=items[1], display_name=items[0], content_type=content_type, field='leave'
            #     )
            #     leave_choices.append(choice)
            sick_Leave = Choice.objects.get(
                name='sick_leave', display_name='Sick leave', content_type=content_type, field='leave'
            )
            pto_leave = Choice.objects.get(
                name='pto', display_name='PTO', content_type=content_type, field='leave'
            )
            leave_types = Choice.objects.filter(content_type=content_type, field='leave').exclude(
                name__in=[sick_Leave.name, pto_leave.name]
            )
            file = open('consultant_leave .csv', 'r')
            reader = csv.reader(file)
            resp_file = open('assignment_resp .csv', 'w')
            writer = csv.writer(resp_file)
            writer.writerow(['Consultant Name', 'Name of Company'])
            i=0
            prev_consultant = ''
            cl = ConsultantLeave.objects.exclude(consultant_id=420)
            cl.delete()
            for item in reader:
                if i == 0:
                    i += 1
                    continue

                consultant = Consultant.objects.filter(name__iexact=item[0]).first()
                if consultant:
                    if item[2] in ['Sick', 'Paid Time Off']:
                        choice = pto_leave if item[2] == 'Paid Time Off' else sick_Leave
                        assigned_leave = ConsultantLeave.objects.filter(
                            consultant=consultant, leave_type=choice, is_expired=False
                        )
                        if assigned_leave:
                            already += 1
                            continue

                    if item[2] == 'Sick':
                        ConsultantLeave.objects.create(
                            year=2022, balance=item[3], granted=item[3],
                            is_expired=False, leave_type=sick_Leave, consultant=consultant
                        )
                        assigned += 1
                    elif item[2] == 'Paid Time Off':
                        ConsultantLeave.objects.create(
                            year=2022, balance=item[3], granted=item[3],
                            is_expired=False, leave_type=pto_leave, consultant=consultant
                        )
                        assigned += 1
                    if prev_consultant == consultant:
                        i+=1
                        continue
                    else:
                        prev_consultant = consultant
                        for choice in leave_types:
                            assigned_leave = ConsultantLeave.objects.filter(
                                consultant=consultant, leave_type=choice, is_expired=False
                            )
                            if assigned_leave:
                                already += 1
                                continue

                            ConsultantLeave.objects.create(
                                year=2022, balance=0, granted=0,
                                is_expired=False, leave_type=choice, consultant=consultant
                            )
                        pass
                    i += 1
                    continue
                writer.writerow([item[0], item[1]])
            print(i-1)
            print(f"Assigned leaves = {assigned}")
            print(f"Already = {already}")
        except Exception as error:
            print(error)
