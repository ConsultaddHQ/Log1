import csv
import json

from django.core.management import BaseCommand

from utils_app.ms_account import MicrosoftAccount
from consultant.models import Consultant


class Command(BaseCommand):
    help = "This command is to create Microsoft account user"

    def handle(self, *args, **options):
        try:
            count = 0
            users, payload = [], []
            ms = MicrosoftAccount()
            with open('Candidate_details.csv', newline='') as csv_file:
                reader = csv.reader(csv_file, delimiter=',', quotechar='|')
                next(reader)
                for row in reader:
                    data = {
                        "email": row[2],
                        "user_id": None,
                        "password": None,
                        "member_id": None,
                        "licence_assigned": False,
                        "consultant_id": None,
                    }
                    qs = Consultant.objects.filter(email__iexact=row[3].lower())
                    if qs:
                        consultant = qs.first()
                        password = f"consultadd@1{consultant.id}23"
                        user = {
                            "last_name": row[2],
                            "first_name": row[1],
                            "log1_email": row[3],
                            "password": password,
                        }
                        users.append(user)
                        data['password'] = password
                        data['consultant_id'] = consultant.id

                        print(data)
                    # Creating Account
                    user_id, msg = ms.create_account(user)
                    data['user_id'] = user_id
                    if msg == 'ok':
                        # Assigning licence
                        if ms.assign_licence(user_id) == "ok":
                            data['licence_assigned'] = True
                            # Assigning Team
                            member_id, msg = ms.assign_team(user_id)
                            if msg == 'ok':
                                data['member_id'] = member_id
                                count += 1
                            else:
                                print(row[0], member_id)
                        else:
                            print(row[0], "Licence not assigned")
                    else:
                        print(row[0], user_id)
                    if row[4] not in payload:
                        payload[row[4]] = data

            if users:
                fields = ['first_name', 'last_name', 'name', 'log1_email', 'email', 'password']
                with open('ms_creds.csv', 'w') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(users)
                with open('ms_database.json', 'w') as file:
                    file.write(json.dumps(payload))
            print(count)
        except Exception as error:
            print(error)
