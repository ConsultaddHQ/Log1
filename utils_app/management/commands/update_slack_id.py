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
            token = "xoxp-3680421803520-3680934465364-5286028512421-9259bb31303bd8acd663f1de3ecbc233"
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            client = WebClient(token=token, ssl=ssl_context)
            result = client.users_list()
            for data in result['members']:
                if data.get('is_email_confirmed') and data['profile'].get('email', None):
                    try:
                        us = User.objects.get(email=data['profile']['email'])
                        if us.slack_id == None:
                            us.slack_id = data['id']
                            us.save()
                            writer.writerow([us.employee_name, True, True, data['id'], data['profile']['email']])
                    except Exception as error:
                        print(error)
                        writer.writerow([data.get('real_name'), False, True, data['id'], data['profile']['email'], error])
                        continue
                else:
                    writer.writerow([data.get('real_name'), False, False, data['id'], data['profile'].get('email', None), 'Email Not Available'])
                    continue
        except Exception as error:
            print(error)
