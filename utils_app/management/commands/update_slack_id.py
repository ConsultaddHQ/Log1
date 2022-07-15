import ssl
import csv
import certifi
from slack_sdk import WebClient
from employee.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open('info.csv', 'w')
            writer = csv.writer(file)
            writer.writerow(['Employee', 'Added', 'Not Found', 'slack_id', 'Email Not Found', 'Issue'])
            token = "xoxp-3680421803520-3680934465364-3787094654406-037dcb80fe47f465f5d92c68950afa35"
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            client = WebClient(token=token, ssl=ssl_context)
            result = client.users_list()
            for data in result['members']:
                if data.get('is_email_confirmed') and data['profile'].get('email', None):
                    try:
                        us = User.objects.get(email=data['profile']['email'])
                        us.slack_id = data['id']
                        us.save()
                        writer.writerow([us.employee_name, True, True, data['id'], data['profile']['email']])
                    except Exception as error:
                        print(error)
                        writer.writerow([data.get('real_name'), False, True, data['id'], data['profile']['email'], error])
                        continue
                else:
                    writer.writerow([data.get('real_name'), False, False, data['id'], data['profile'].get('email', None), 'Email Not Available'])
        except Exception as error:
            print(error)
