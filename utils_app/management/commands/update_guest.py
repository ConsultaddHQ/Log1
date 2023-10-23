
from django.core.management import BaseCommand

from marketing.models import Interview, GuestInfo


type_mapper = {
    "coder": "Coder",
    "assigned": "Assigned",
    "not_required": "Not Required"
}


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            int_qs = Interview.objects.all()
            for obj in int_qs:
                obj.guest_type = type_mapper.get(obj.guest_type)
                obj.save()
                eng_guest_qs = obj.guest.filter(role__name='engineer')
                other_guest_qs = obj.guest.exclude(role__name='engineer')
                guests = obj.guests.all()
                for guest_obj in eng_guest_qs:
                    info_obj = GuestInfo.objects.filter(user=guest_obj, type='Coder').first()
                    if not info_obj:
                        info_obj = GuestInfo.objects.create(user=guest_obj, type="Coder")
                    if info_obj not in guests:
                        obj.guests.add(info_obj)
                        obj.save()
                for guest_obj in other_guest_qs:
                    info_obj = GuestInfo.objects.filter(user=guest_obj, type='Other').first()
                    if not info_obj:
                        info_obj = GuestInfo.objects.create(user=guest_obj, type="Other")
                    if info_obj not in guests:
                        obj.guests.add(info_obj)
                        obj.save()
                obj.guest.clear()
        except Exception as error:
            print(error)
