from marketing.models import Lead, Submission
from employee.models import Role
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "This is one time command to move user avatar to AWS-S3 bucket"

    def handle(self, *args, **options):
        try:
            # leads = Lead.objects.all()
            # for lead in leads:
            #     if lead.is_w2:
            #         lead.position_type='w2'
            #         lead.save()
            # subs = Submission.objects.all()
            # for sub in subs:
            #     if sub.lead.is_w2:
            #         sub.work_type='w2'
            #         sub.save()
            for role in Role.objects.all():
                role.display_name = role.name.capitalize()
                role.save()
        except Exception as error:
            print(error)
