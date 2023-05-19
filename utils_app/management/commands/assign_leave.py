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
            count, created, assigned, already = 0, 0, 0, 0
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
            file = open('consultant_leave.csv', 'r')
            reader = csv.reader(file)
            resp_file = open('assignment_resp .csv', 'w')
            writer = csv.writer(resp_file)
            writer.writerow(['Consultant Name', 'Name of Company'])
            resp_file = open('already_resp .csv', 'w')
            writer_el = csv.writer(resp_file)
            writer_el.writerow(['serial_number', 'Consultant Name', 'Name of Company', 'leave_type', 'Leave Count'])
            i=0
            prev_consultant = ''
            cl = ConsultantLeave.objects.exclude(consultant_id=420)
            cl.delete()
            for item in reader:
                count = count + 1
                if i == 0:
                    i += 1
                    continue
                name = item[0].replace(" ", "").split(',')
                consultant_name = " ".join([name[1], name[0]])
                consultant = Consultant.objects.filter(name__iexact=consultant_name).first()
                if consultant:
                    if item[2] in ['Sick', 'Paid Time Off']:
                        choice = pto_leave if item[2] == 'Paid Time Off' else sick_Leave
                        ConsultantLeave.objects.create(
                            year=2022, balance=item[3], granted=item[3],
                            is_expired=False, leave_type=choice, consultant=consultant
                        )
                        assigned += 1

                        # assigned_leave = ConsultantLeave.objects.filter(
                        #     consultant=consultant, leave_type=choice, is_expired=False
                        # )
                        # if assigned_leave:
                        #     writer_el.writerow([count, consultant_name, item[1], choice.name, item[3]])
                        #     already += 1
                        #     continue
                        # else:

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
                                writer_el.writerow([count, consultant_name, item[1], choice.name, item[3]])
                                already += 1
                                continue

                            ConsultantLeave.objects.create(
                                year=2022, balance=0, granted=0,
                                is_expired=False, leave_type=choice, consultant=consultant
                            )
                        pass
                    i += 1
                    continue
                writer.writerow([count, consultant_name, item[1]])
            print(i-1)
            print(f"Assigned leaves = {assigned}")
            print(f"Already = {already}")
            print(f"Created = {created}")
            print(f"Count = {count}")
        except Exception as error:
            print(error)
