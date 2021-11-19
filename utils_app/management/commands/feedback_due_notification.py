from django.core.management import BaseCommand

from constance import config
from employee.models import User
from marketing.models import Interview, Test
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    # A command must define handle()
    def handle(self, *args, **options):
        job = create_cron_object(name='feedback_due_notification')
        try:
            interview_text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                            <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>"""
            test_text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                            <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>"""
            marketers = User.objects.filter(
                is_active=True, role__name='marketer', team__dept="Marketing"
            ).order_by('team__name')
            count_interview_marketers = 0
            count_test_marketers = 0
            for user in marketers:
                interview_count = Interview.objects.filter(submission__created_by=user, status='feedback_due').count()
                if interview_count != 0:
                    count_interview_marketers = count_interview_marketers+1
                    interview_text += f"""<tr>
                                    <td style="padding:5px 8px 5px 8px;">{count_interview_marketers}</td>
                                    <td style="padding:5px 8px 5px 8px;">{user.employee_name}</td>
                                    <td style="text-align: center;padding:5px 8px 5px 8px;">{interview_count}</td>
                                </tr>\n"""
                    if count_interview_marketers % 50 == 0:
                        data = {
                            "title": "Interviews count for feedback due status",
                            "text": f"""<table border='2' style='border-collapse:collapse'>{interview_text}</table>"""
                        }
                        res, msg = post_msg_using_webhook(config.announcement_url, data)
                        if msg == 'error':
                            raise Exception(res)
                        interview_text = f""" <tr>
                                                    <th style="padding:5px 8px 5px 8px;">#</th>
                                                    <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                                    </tr>"""
                test_count = Test.objects.filter(submission__created_by=user, status='feedback_due').count()
                if test_count != 0:
                    count_test_marketers = count_test_marketers+1
                    test_text += f"""<tr>
                                    <td style="padding:5px 8px 5px 8px;">{count_test_marketers}</td>
                                    <td style="padding:5px 8px 5px 8px;">{user.employee_name}</td>
                                    <td style="text-align: center;padding:5px 8px 5px 8px;">{test_count}</td>
                                </tr>\n"""
                    if count_test_marketers % 50 == 0:
                        data = {
                            "title": "Test count for feedback due status",
                            "text": f"""<table border='2' style='border-collapse:collapse'>{test_text}</table>"""
                        }
                        res, msg = post_msg_using_webhook(config.announcement_url, data)
                        if msg == 'error':
                            raise Exception(res)
                        test_text = f""" <tr>
                                                    <th style="padding:5px 8px 5px 8px;">#</th>
                                                    <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                                    </tr>"""
            if count_interview_marketers % 50 != 0:
                interview_data = {
                    "title": "Interviews count for feedback due status",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{interview_text}</table>"""
                }
                res, msg = post_msg_using_webhook(config.marketing_report_url, interview_data)
                if msg == 'error':
                    raise Exception(res)
            if count_test_marketers % 50 != 0:
                test_data={
                        "title": "test count for feedback due status",
                        "text": f"""<table border='2' style='border-collapse:collapse'>{test_text}</table>"""
                    }
                res1, msg1 = post_msg_using_webhook(config.marketing_report_url, test_data)
                if msg1 == 'error':
                    raise Exception(res1)
        except Exception as error:
            create_cron_error(job, error)
