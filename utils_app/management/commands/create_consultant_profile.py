# from django.core.management import BaseCommand
#
# from employee.models import User
# from consultant.models import Consultant
# from log1.utils import password_generator
#
#
# class Command(BaseCommand):
#     help = "This command is for creating consultant profiles"
#
#     def handle(self, *args, **options):
#         try:
#
#             user_dict = [
#                 {"name": "Suchita Bhoomkar", "email": "suchita.svb@gmail.com"}
#                 # {"name": "Subodh Dubey", "email": "subodh@cloudtech.com"},
#                 # {"name": "Giorgio Mazza", "email": "giorgio@cloudtech.com"}
#             ]
#             for obj in user_dict:
#                 consultant, _ = Consultant.objects.get_or_create(email=obj.get("email"))
#                 consultant.gender = "female"
#                 consultant.is_active = True
#                 consultant.remote_only = True
#                 consultant.name = obj.get("name")
#                 consultant.save()
#
#         except Exception as error:
#             print(str(error))
import csv
import random
from datetime import datetime
from django.core.management import BaseCommand

from consultant.models import Consultant, WorkAuth, PayrollEmployer
from utils_app.models import Choice


def convert_date(date_str):
    return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            # file_ = open("CAPS Employee Creds.csv", "w")
            # file = open("CAPS Employee.csv", "r")
            # reader = csv.reader(file)
            # writer = csv.writer(file_)
            # writer.writerow(["Name", "Email", "Password"])
            count = 0
            # for row in reader:
            #     if count < 2:
            #         count += 1
            #         continue
            # con_obj = Consultant.objects.get(email=row[1])
            con_obj = Consultant.objects.get(
                email="pruthvikpatel99@gmail.com", name="Pruthvik Patel", phone_no="73287422705"
            )
            if not con_obj.is_active:
                con_obj.is_active = True
            password = f"caps@2026{random.choice([2, 43, 5 ,7])}"
            con_obj.set_password(password)
            con_obj.save()
                # writer.writerow([con_obj.name, con_obj.email, password])
            visa_type = Choice.objects.get(name="opt", field="visa_usa")
            WorkAuth.objects.create(
                consultant=con_obj, visa_type=visa_type.name,
                visa_start=convert_date("08/11/2025"), visa_end=convert_date("08/11/2025")
            )
            PayrollEmployer.objects.create(
                name="CAPS", start=convert_date("08/11/2025"), consultant=con_obj)
            print(password)
            
        except Exception as error:
            print(f"{error}")
