from django.core.management import BaseCommand
from consultant.models import Consultant
from marketing.models import Interview
import csv 

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            fields = ['Sl no', 'Consultant Name', 'Client Name'] 
            offer_interview = Interview.objects.filter(status='offer').order_by('id').distinct()
            w2_consultant = Consultant.objects.filter(is_w2 = True)
            ids = []
            for con in w2_consultant:
                ids.append(con.id)
            results = offer_interview.filter(submission__consultant_marketing__consultant__id__in=ids)
            sl = 1
            breakpoint()
            with open("data.csv", 'w') as csvfile:
                csvwriter = csv.writer(csvfile) 
                csvwriter.writerow(fields) 
                for result in results:
                    rows = [sl, result.consultant.name, result.submission.client]
                    csvwriter.writerow(rows)
                    sl+=1
        except Exception as error:
            print(error)