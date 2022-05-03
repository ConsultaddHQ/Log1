from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from marketing.models import Test, Interview
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='test/interview_in_feedback_due')
        try:
            payload = {}
            date_passed = date.today() - timedelta(days=15)
            test_lst = Test.objects.filter(status='feedback_due').exclude(
                modified__range=[date_passed, date.today()])
            interview_lst = Interview.objects.filter(status='feedback_due').exclude(
                modified__range=[date_passed, date.today()])
            for test in test_lst:
                count = 1
                if test.marketer.employee_name in payload.keys():
                    payload[test.marketer.employee_name]["count"] = payload[test.marketer.employee_name]['count'] + 1
                else:
                    payload[test.marketer.employee_name] = {
                        "count": count,
                        "pending_for": "test",
                        "team": test.marketer.team.name,
                    }

            for interview in interview_lst:
                count = 1
                if interview.marketer.employee_name in payload.keys():
                    if payload[interview.marketer.employee_name]["pending_for"] == "test":
                        payload[interview.marketer.employee_name]["pending_for"] = "test | interview"
                    payload[interview.marketer.employee_name]["count"] = payload[interview.marketer.employee_name][
                                                                             'count'] + 1
                else:
                    payload[interview.marketer.employee_name] = {
                        "count": count,
                        "pending_for": "interview",
                        "team": interview.marketer.team.name,
                    }

            column_names = f""" <tr>
                <th style="padding:5px 8px 5px 8px;">#</th>
                <th style="padding:5px 8px 5px 8px;">Marketer</th>
                <th style="padding:5px 8px 5px 8px;">Team</th>
                <th style="padding:5px 8px 5px 8px;">Test, Interview</th>
                <th style="padding:5px 8px 5px 8px;">Count</th>
                </tr>"""
            if payload != {}:
                text = column_names
                index = 0
                for item in payload:
                    text += f"""<tr>
                                    <td style="padding:5px 8px 5px 8px;"> {index+1} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {item} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {payload[item]['team']} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {payload[item]['pending_for']} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {payload[item]['count']} </td>
                                </tr>"""
                    index = index + 1
                    if index == 46:
                        data = {
                            "title": "Marketers whose tests/interviews are in feedback due status",
                            "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
                        }
                        res, msg = post_msg_using_webhook(config.engineering_url, data)
                        if msg == 'error':
                            print(res)
                            continue
                        text, index = column_names, 0

                data = {
                    "title": "Marketers whose tests/interviews are in feedback due status",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
                }
            else:
                data = {
                    "title": "Marketers whose tests/interviews are in feedback due status",
                    "text": "No Pending test"
                }

            res, msg = post_msg_using_webhook(config.engineering_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
