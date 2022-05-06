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
                    qs = Consultant.objects.filter(email=row[3].lower())
                    if qs:
                        consultant = qs.first()
                        password = f"consultadd@1{consultant.id}23"
                        user = {
                            "name": row[0],
                            "email": row[2],
                            "log1_email": row[1],
                            "password": password,
                            "first_name": row[0].split(' ')[0],
                            "last_name": " ".join(row[0].split(' ')[1:]),
                        }
                        users.append(user)
                        data['password'] = password
                        data['consultant_id'] = consultant.id

                        print(data)
                    # Creating Account
                    user_id, msg = ms.create_account(user)
                    if msg == 'ok':

                        data['user_id'] = user_id
                        # Assigning licence
                        if ms.assign_licence(user_id) == "ok":
                            data['licence_assigned'] = True
                            # Assigning Team
                            member_id, msg = ms.assign_team(user_id)
                            if msg == 'ok':
                                data['member_id'] = member_id
                                print(row[2])
                                count += 1
                            else:
                                print(row[2], member_id)
                        else:
                            print(row[2], "Licence not assigned")
                    else:
                        print(row[2], user_id)
                    if row[4] not in payload:
                        payload[row[4]] = data

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
