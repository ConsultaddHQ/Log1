import csv
from django.core.management import BaseCommand

from project.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open('PO_detail.csv', 'w+')
            writer = csv.writer(file)
            monthly = {
                "January": {
                    "2023": ["2023-01-01", "2023-02-01"],
                    "2024": ["2024-01-01", "2024-02-01"]
                },
                "February": {
                    "2023": ["2023-02-01", "2023-03-01"],
                    "2024": ["2024-02-01", "2024-03-01"]
                },
                "March": {
                    "2023": ["2023-03-01", "2023-04-01"],
                    "2024": ["2024-03-01", "2024-04-01"]
                },
                "April": {
                    "2023": ["2023-04-01", "2023-05-01"],
                    "2024": ["2024-04-01", "2024-05-01"]
                },
                "May": {
                    "2023": ["2023-05-01", "2023-06-01"],
                    "2024": ["2024-05-01", "2024-06-01"]
                },
                "June": {
                    "2023": ["2023-06-01", "2023-07-01"],
                    "2024": ["2024-06-01", "2024-07-01"]
                },
                "July": {
                    "2023": ["2023-07-01", "2023-08-01"],
                    "2024": ["2024-07-01", "2024-08-01"]
                },
                "August": {
                    "2023": ["2023-08-01", "2023-09-01"],
                    "2024": ["2024-08-01", "2024-09-01"]
                },
                "September": {
                    "2023": ["2023-09-01", "2023-10-01"],
                    "2024": ["2024-09-01", "2024-10-01"]
                },
                "October": {
                    "2023": ["2023-10-01", "2023-11-01"],
                    "2024": ["2024-10-01", "2024-11-01"]
                },
                "November": {
                    "2023": ["2023-11-01", "2023-12-01"],
                    "2024": ["2024-11-01", "2024-12-01"]
                },
                "December": {
                    "2023": ["2023-12-01", "2024-01-01"],
                    "2024": ["2024-12-01", "2025-01-01"]
                }
            }
            writer.writerow([
                'Month', '2023-C2C Offer', '2023-C2C Joining', '2023-C2C Termination', '2023-W2 Offer',
                '2023-W2 Joining', '2023-W2 Termination', '2024-C2C Offer', '2024-C2C Joining', '2024-C2C Termination',
                '2024-W2 Offer', '2024-W2 Joining', '2024-W2 Termination',
            ])
            for key in monthly.keys():
                c2c_offer_2023 = Project.objects.filter(
                    statuses__status='received', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2023']
                ).count()
                w2_offer_2023 = Project.objects.filter(
                    statuses__status='received', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2023']
                ).count()
                c2c_joined_2023 = Project.objects.filter(
                    statuses__status='joined', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2023']
                ).count()
                w2_joined_2023 = Project.objects.filter(
                    statuses__status='joined', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2023']
                ).count()
                c2c_termination_2023 = Project.objects.filter(
                    statuses__status__istartswith='terminated', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2023'], is_remote=True
                ).count()
                w2_termination_2023 = Project.objects.filter(
                    statuses__status__istartswith='terminated', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2023'], is_remote=True
                ).count()
                c2c_offer_2024 = Project.objects.filter(
                    statuses__status='received', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2024']
                ).count()
                w2_offer_2024 = Project.objects.filter(
                    statuses__status='received', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2024']
                ).count()
                c2c_joined_2024 = Project.objects.filter(
                    statuses__status='joined', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2024']
                ).count()
                w2_joined_2024 = Project.objects.filter(
                    statuses__status='joined', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2024']
                ).count()
                c2c_termination_2024 = Project.objects.filter(
                    statuses__status__istartswith='terminated', submission__work_type='c2c',
                    statuses__created__range=monthly.get(key)['2024'], is_remote=True
                ).count()
                w2_termination_2024 = Project.objects.filter(
                    statuses__status__istartswith='terminated', submission__work_type__in=['w2', 'full_time'],
                    statuses__created__range=monthly.get(key)['2024'], is_remote=True
                ).count()

                writer.writerow([
                    key, c2c_offer_2023, c2c_joined_2023, c2c_termination_2023, w2_offer_2023, w2_joined_2023,
                    w2_termination_2023, c2c_offer_2024, c2c_joined_2024, c2c_termination_2024, w2_offer_2024,
                    w2_joined_2024, w2_termination_2024
                ])
        except Exception as error:
            print(error)
