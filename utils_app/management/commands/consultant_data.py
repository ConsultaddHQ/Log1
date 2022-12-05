from django.core.management import BaseCommand
from consultant.models import Consultant
from marketing.models import Interview
import csv 

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            fields = ['Sl no', 'Consultant Name', 'Client name', 'Vendor name', 'Fail Resone']
            fail_interview = Interview.objects.filter(status='failed').order_by('id').distinct()
            consultants_id_list = []
            # get all consultants
            with open('data1.csv', mode ='r')as file:
                csvFile = csv.reader(file)            
                for lines in csvFile:
                    if lines[0] != "" and lines[0] != 'Internal' and lines[0] != 'Name':
                        consultant = Consultant.objects.filter(name = lines[0]).first()
                        consultants_id_list.append(consultant.id)
            results = fail_interview.filter(submission__consultant_marketing__consultant__id__in=consultants_id_list)
            sl = 1
            with open("failed_data.csv", 'w') as csvfile:
                csvwriter = csv.writer(csvfile) 
                csvwriter.writerow(fields) 
                for result in results:
                    rows = [sl, result.consultant.name, result.submission.client, result.submission.vendor.name, result.failure_reason]
                    csvwriter.writerow(rows)
                    sl+=1
        except Exception as error:
            print(error)