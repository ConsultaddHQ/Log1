from django.core.management import BaseCommand

from marketing.models import Interview


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            count = 0
            queryset = Interview.objects.filter(guest_type__in=["AssignedCoder", "AssignedAssistance", "AssignedCoder & Assistance"])
            for obj in queryset:
                if obj.guest_type == "AssignedCoder":
                    count += 1
                    if obj.guests.filter(user__role__name='engineer'):
                        obj.guest_type = "Assigned Coder"
                    else:
                        obj.guest_type = "Coder"
                    obj.save()
                elif obj.guest_type == "AssignedAssistance":
                    count += 1
                    if obj.guests.filter(user__role__name='engineer'):
                        obj.guest_type = "Assigned Assistance"
                    else:
                        obj.guest_type = "Assistance"
                    obj.save()
                elif obj.guest_type == "AssignedCoder & Assistance":
                    count += 1
                    if obj.guests.filter(user__role__name='engineer'):
                        obj.guest_type = "Assigned Coder & Assistance "
                    else:
                        obj.guest_type = "Coder & Assistance"
                    obj.save()
            print(count)
        except Exception as error:
            print(error)
