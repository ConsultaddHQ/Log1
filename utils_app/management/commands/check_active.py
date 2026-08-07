import csv
from django.core.management import BaseCommand
from django.shortcuts import get_object_or_404

from googleapiclient.discovery import build
from employee.models import User, Role, Team
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/admin.directory.user"]
creds = Credentials.from_authorized_user_file("google_token.json", SCOPES)
service = build("admin", "directory_v1", credentials=creds)


def required_data(all_users):
    required_data = [{
        "Name": _user['name']['fullName'], "Email": _user['primaryEmail'],
        "IsSuspended": _user.get('suspended'), "IsAdmin": _user.get('isAdmin')
    } for _user in all_users]
    return required_data


class Command(BaseCommand):
    help = "This command is to get user from CSV file."

    def handle(self, *args, **options):
        all_users = list()
        not_active = list()
        next_page_token = None
        try:
            while True:
                results = service.users().list(
                    customer="my_customer", orderBy="email", pageToken=next_page_token
                ).execute()
                users = results.get("users", []) if results else []
                for item in users:
                    try:
                        user_obj = get_object_or_404(User, email__iexact=item.get('primaryEmail'))
                        if not user_obj.is_active:
                            not_active.append(item)
                    except Exception as e:
                        all_users.append(item)

                next_page_token = results.get('nextPageToken', None)
                if not next_page_token:
                    break

            csv_file = open("not_found_user.csv", 'w+')
            writer = csv.writer(csv_file)
            writer.writerow(["Name", "Email"])
            for item in all_users:
                writer.writerow([
                    item['name']['fullName'], item['primaryEmail']
                ])
        except Exception as error:
            print(error)
