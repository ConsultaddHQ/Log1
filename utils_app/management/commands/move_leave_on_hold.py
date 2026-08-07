from django.core.management import BaseCommand

from project.models import Project, ConsultantLeave


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            active_consultants = Project.objects.filter(
                statuses__status='joined', statuses__is_current=True).values_list(
                'consultant_id', 'submission__consultant_marketing__consultant_id'
            )
            flat_data = [item for sublist in active_consultants for item in sublist]
            lst_data = list(set(flat_data))

            on_hold_leaves = ConsultantLeave.objects.filter(year=2024, is_expired=False).exclude(
                consultant_id__in=lst_data)
            for leave in on_hold_leaves:
                leave.on_hold = True
                leave.save()
        except Exception as error:
            print(str(error))
