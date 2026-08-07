from django.core.management import BaseCommand

from project.models import ConsultantLeave


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            consultant_leave_qs = ConsultantLeave.objects.filter(year=2024, is_expired=True)
            for obj in consultant_leave_qs:
                if not obj.is_expired:
                    print(f"{obj.consultant.name} {obj.leave_type.display_name} is not expired")
                obj.is_expired = False
                # obj.save()
        except Exception as error:
            print("test")
