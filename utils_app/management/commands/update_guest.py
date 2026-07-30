#
# from django.core.management import BaseCommand
#
# from marketing.models import Interview, GuestInfo
#
#
# type_mapper = {
#     "coder": "Coder",
#     "assigned": "Assigned Coder",
#     "not_required": "Not Required"
# }
#
#
# class Command(BaseCommand):
#     def handle(self, *args, **options):
#         try:
#             int_qs = Interview.objects.all()
#             for obj in int_qs:
#                 obj.guest_type = type_mapper.get(obj.guest_type)
#                 obj.save()
#                 eng_guest_qs = obj.guest.filter(role__name='engineer')
#                 other_guest_qs = obj.guest.exclude(role__name='engineer')
#                 guests = obj.guests.all()
#                 for guest_obj in eng_guest_qs:
#                     info_obj = GuestInfo.objects.filter(user=guest_obj, type='Coder').first()
#                     if not info_obj:
#                         info_obj = GuestInfo.objects.create(user=guest_obj, type="Coder")
#                     if info_obj not in guests:
#                         obj.guests.add(info_obj)
#                         obj.save()
#                 for guest_obj in other_guest_qs:
#                     info_obj = GuestInfo.objects.filter(user=guest_obj, type='Other').first()
#                     if not info_obj:
#                         info_obj = GuestInfo.objects.create(user=guest_obj, type="Other")
#                     if info_obj not in guests:
#                         obj.guests.add(info_obj)
#                         obj.save()
#                 obj.guest.clear()
#         except Exception as error:
#             print(error)

import csv
from django.core.management import BaseCommand

from marketing.models import Interview


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            file = open("interview_updates.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["Interview ID", "Prev Guest Type", "Updated Guest Type", "Interview Status", "Created At"])
            # interview_qs = Interview.objects.filter(status__in=['offer', 'failed', 'cancelled', 'next_round'])
            interview_qs = Interview.objects.all().order_by('modified')
            for obj in interview_qs:
                if obj.status in ['offer', 'failed', 'cancelled', 'next_round']:
                    if obj.coding_present and obj.assistance_required:
                        if obj.guests.filter(type__in=['Assistant', 'Coder', 'Coder & Assistant']):
                            if obj.guest_type != 'Assigned Coder & Assistance':
                                writer.writerow(
                                    [obj.id, obj.guest_type, 'Assigned Coder & Assistance', obj.get_status_display(), obj.created])
                                obj.guest_type = 'Assigned Coder & Assistance'
                        else:
                            writer.writerow([obj.id, obj.guest_type, 'Not Updated', obj.get_status_display(), obj.created])
                            pass

                    elif obj.coding_present:
                        if obj.guests.filter(type__in=['Coder']):
                            if obj.guest_type != 'Assigned Coder':
                                writer.writerow([obj.id, obj.guest_type, 'Assigned Coder', obj.get_status_display(), obj.created])
                                obj.guest_type = 'Assigned Coder'
                            else:
                                writer.writerow([obj.id, obj.guest_type, 'Not Updated', obj.get_status_display(), obj.created])

                    elif obj.assistance_required:
                        if obj.guests.filter(type__in=['Assistant']):
                            if obj.guest_type != 'Assigned Assistant':
                                writer.writerow([obj.id, obj.guest_type, 'Assigned Assistant', obj.get_status_display(), obj.created])
                                obj.guest_type = 'Assigned Assistant'
                            else:
                                writer.writerow([obj.id, obj.guest_type, 'Not Updated', obj.get_status_display(), obj.created])

                    elif not obj.assistance_required and not obj.coding_present and obj.guest_type != 'Not Required':
                        writer.writerow([obj.id, obj.guest_type, 'Not Required', obj.get_status_display(), obj.created])
                        obj.guest_type = 'Not Required'

                    elif obj.guest_type is None:
                        obj.guest_type = 'Not Required'
                    obj.save()

                elif obj.status in ['scheduled', 'rescheduled', 'cancelled'] and obj.guest_type != 'Not Required':
                    if obj.guests.all() and obj.guest_type in ['Coder', 'coder', 'Assistance', 'Coder & Assistance']:
                        obj.guest_type = 'Assigned' + obj.guest_type
                    elif obj.guest_type is None:
                        obj.guest_type = 'Not Required'
                    obj.save()

                elif obj.status == 'feedback_due' and obj.guest_type != 'Not Required':
                    if obj.guests.all() and obj.guest_type in ['Coder', 'coder', 'Assistance', 'Coder & Assistance']:
                        obj.guest_type = 'Assigned' + obj.guest_type
                    elif obj.guest_type is None:
                        obj.guest_type = 'Not Required'
                    obj.save()

        except Exception as error:
            print(error)
