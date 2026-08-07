import csv
from constance import config
from django.core.management import BaseCommand

from project.models import ProjectPaymentTerm
from project.serializers import ProjectPaymentTermSerializer


class Command(BaseCommand):

    def handle(self, *args, **options):

        try:
            file = open('Remote Details.csv', "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Consultant Name", "Client", "Vendor", "Remote Engineer", "Marketer",
                "PO Rate", "Company Payment Term", "Consultant Payment Term", "Project ID", "App Link"
            ])
            queryset = ProjectPaymentTerm.objects.all()
            serializer = ProjectPaymentTermSerializer(queryset, many=True)
            for data in serializer.data:
                project = data.get('project')
                writer.writerow([
                    project.get('consultant_name'), project.get('client_name'), project.get('vendor_company'),
                    project.get('remote_engineer'), project.get('marketer_name'), project.get('rate'),
                    data.get('payment_term'), data.get('consultant_payment_term'), project.get('project_id'),
                    F"{config.APP_URL}/#/details/{project.get('submission_id')}/project?id={project.get('project_id')}"
                ])
        except Exception as error:
            print(error)
