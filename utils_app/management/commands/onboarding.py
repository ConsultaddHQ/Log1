from django.core.management import BaseCommand

from employee.models import User

from project.views import ProjectViewSets, Project

obj = ProjectViewSets

scrum_masters = list(User.objects.filter(
    team__name="Zioqu", role__name__in=['admin', 'proxy'], account_login=True
).values_list('email', flat=True))


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            project = Project.objects.get(id=1479)
            # offer_res, offer_msg = obj.send_offer_received_mail(project, scrum_masters, None)
            support_res, support_msg = obj.send_support_mail(project, scrum_masters, None)

            # print(offer_msg)
            # print(offer_res)
            print(support_msg)
            print(support_res)
        except Exception as error:
            print(error)
