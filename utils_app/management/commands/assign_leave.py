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
            leave_choices = []
            content_type = ContentType.objects.get(model='consultantleave')
            consultants = Consultant.objects.filter(status='on_project')
            leave_types = {
                'Sick leave': 'sick_leave',
                'PTO': 'pto',
                'Maternity': 'maternity',
                'Paternity': 'paternity',
                'Marriage leave': 'marriage_leave',
                'Covid emergency sick leave': 'covid_emergency_sick_leave'
            }
            for items in leave_types.items():
                choice = Choice.objects.create(
                    name=items[1], display_name=items[0], content_type=content_type, field='leave'
                )
                leave_choices.append(choice)
            for consultant in consultants:
                for choice in leave_choices:
                    assigned_leave = ConsultantLeave.objects.filter(consultant=consultant, leave_type=choice, is_expired=True)
                    if assigned_leave:
                        already += 1
                        continue
                    ConsultantLeave.objects.create(
                        year=2022, balance=82.0, granted=82.0,
                        is_expired=False, leave_type=choice, consultant=consultant
                    )
                    assigned += 1
            print(len(consultants))
            print(f"Assigned leaves = {assigned}")
            print(f"Already = {already}")
        except Exception as error:
            print(error)
