from django.core.management import BaseCommand

from consultant.models import ConsultantMarketing


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            open_marketing_obj = ConsultantMarketing.objects.get(id=2226)
            to_delete_marketing_obj = ConsultantMarketing.objects.get(id=2211)
            submissions_qs = to_delete_marketing_obj.submissions.all()
            for submission_obj in submissions_qs:
                submission_obj.consultant_marketing = open_marketing_obj
                submission_obj.save()
            to_delete_marketing_obj.delete()
        except Exception as error:
            print(error)
