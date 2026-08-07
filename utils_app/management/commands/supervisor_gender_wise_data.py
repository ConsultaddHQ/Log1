import csv
from django.core.management import BaseCommand

from utils_app.models import Choice
from marketing.models import Interview


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            file = open("SupervisorData.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["Position", "Total", "Male", "Female"])
            int_qs = Interview.objects.filter(start_time__gt='2023-12-31', start_time__lt='2024-06-22').exclude(
                status='cancelled').exclude(submission__status='archive')
            positions = Choice.objects.filter(content_type__model='lead', field='position')

            total_interview_count = int_qs.count()
            total_interview_male = int_qs.filter(submission__consultant_marketing__consultant__gender='male').count()
            total_interview_female = int_qs.filter(submission__consultant_marketing__consultant__gender='female').count()
            for pos in positions:
                int_position_qs = int_qs.filter(submission__lead__position=pos)
                male = int_position_qs.filter(submission__consultant_marketing__consultant__gender='male').count()
                female = int_position_qs.filter(submission__consultant_marketing__consultant__gender='female').count()
                writer.writerow([pos.display_name, int_position_qs.count(), male, female])
            writer.writerow(["Total", total_interview_count, total_interview_male, total_interview_female])
        except Exception as error:
            print(error)