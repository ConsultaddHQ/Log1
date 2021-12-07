import csv
from django.core.management import BaseCommand

from utils_app.ms_account import MicrosoftAccount
from consultant.models import Consultant, MSAccount


class Command(BaseCommand):
    help = "This command is to create Microsoft account user"

    def handle(self, *args, **options):
        try:
            users, not_found = [], []
            ms = MicrosoftAccount()
            with open('employees_data.csv', newline='') as csv_file:
                reader = csv.reader(csv_file, delimiter=',', quotechar='|')
                next(reader)
                for row in reader:
                    qs = Consultant.objects.filter(email=row[1].lower())
                    if qs:
                        consultant = qs.first()
                        user = {
                            "name": row[0],
                            "email": row[2],
                            "log1_email": row[1],
                            "first_name": row[0].split()[0],
                            "last_name": " ".join(row[0].split()[1:]),
                            # "password": f"consultadd@1{consultant.id}23"
                        }
                        users.append(user)
                    else:
                        print(row[1].lower())
                        not_found.append({
                            "name": row[0],
                            "email": row[2],
                            "log1_email": row[1],
                            "first_name": row[0].split()[0],
                            "last_name": " ".join(row[0].split()[1:]),
                        })

                    fields = ['first_name', 'last_name', 'name', 'log1_email', 'email']
                    with open('employees_not_found.csv', 'w') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(not_found)

                    # account, _ = MSAccount.objects.get_or_create(
                    #     consultant=consultant,
                    # )
                    # account.email = user['email']
                    # account.save()
            #     # Creating Account
            #     user_id, msg = ms.create_account(user)
            #     if msg == 'ok':
            #         account.user_id = user_id
            #         # Assigning licence
            #         if ms.assign_licence(user_id) == "ok":
            #             account.licence_assigned = True
            #             # Assigning Team
            #             member_id, msg = ms.assign_team(user_id)
            #             if msg == 'ok':
            #                 account.member_id = member_id
            #       account.save()

        except Exception as error:
            print(error)
