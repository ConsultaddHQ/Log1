from datetime import datetime
from django.core.management import BaseCommand

from consultant.models import Consultant, ConsultantRateRevision, PayrollEmployer
import requests
import json
import os


def get_hubspot_data(email):
    key = os.environ.get('HUBSPOT_KEY')
    url = f"https://api.hubapi.com/contacts/v1/contact/email/{email}/profile?hapikey={key}"
    r = requests.get(url=url)
    r = json.loads(r.text)
    if 'properties' in r and 'payroll_through' in r['properties']:
        data = {
            "employer": r['properties']['payroll_through']['value'] if 'payroll_through' in r['properties'] else None,
            "timestamp":  r['properties']['payroll_through']["versions"][0]['timestamp']
        }
        return data
    else:
        return None


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):

        # import pandas as pd
        #
        # df = pd.read_excel("../final hubspot.xlsx")
        # df.fillna('', inplace=True)
        # payload = dict()
        # # id = [79,201,254,44,255,292,202,50,304,102,229,317,332,330,287,308,434,386,263,401,144,251,268,337,28,409]
        # for index, row in df.iterrows():
        #     if row['Log1 Email ID']:
        #         consultant = Consultant.objects.filter(email=str(row['Log1 Email ID']).strip()).first()
        #         if consultant:
        #             print(row['Hubspot Email'])
        #             data = get_hubspot_data(row['Hubspot Email'])
        #             if data and data['employer']:
        #                 timestamp = int(data['timestamp'])/1000
        #                 date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
        #                 payload[consultant.email] = {
        #                     "date": date,
        #                     "payroll_employer": data['employer'],
        #                 }
        # file = open('../hubspot_employer.json', 'w')
        # file.write(json.dumps(payload))
        # file.close()

        file = open('../hubspot_employer.json', 'r')
        docs = json.loads(file.read())
        file.close()
        count = 0
        for email, docs in docs.items():
            print(docs)
            print(email)
            count += 1
            con = Consultant.objects.get(email=email)
            obj = {
                "Consultadd Inc": "Consultadd",
                "Nzyme Inc": "Nzyme",
                "Okyte Inc": "Okyte",
                "Oc10 Inc": "OC10",
                "Zioqu Inc": "Zioqu",
                "NetResolute Inc": "NetResolute",
                "Pythonwise Inc": "Pythonwise",
                "Induci Inc": "Induci",
                "Boto3 Inc": "Boto3",
                "Gokronos Inc": "GoKronos",
                "Ioneq Inc": "Ioneq",
                "Datayog Inc": "Datayog"
            }
            PayrollEmployer.objects.create(
                name=obj[docs['payroll_employer']],
                start=docs['date'],
                consultant=con
            )



        #     if docs['rate'] != con.rate:
        #         prev_rate = con.rates.filter(end=None).first()
        #         if prev_rate:
        #             prev_rate.end = docs['date']
        #             prev_rate.save()
        #         ConsultantRateRevision.objects.create(
        #             rate=docs['rate'],
        #             previous_rate=prev_rate.rate if prev_rate else 0,
        #             start=docs['date'],
        #             consultant=con
        #         )
        #     if docs['phone_no']:
        #         con.phone_no = str(docs['phone_no']).split(',')[0]
        #         con.save()
        # print(count)
