from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from marketing.models import Interview, Test
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object, write_exception


class Command(BaseCommand):

    def handle(self, *args, **options):
        job = create_cron_object(name='feedback_due_notification')
        try:
            count_tests, count_interviews, count_coder = 0, 0, 0
            interview_text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                            <th style="padding:5px 8px 5px 8px;">Interview Ids</th>
                            <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>"""
            test_text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                            <th style="padding:5px 8px 5px 8px;">Test ids</th>
                            <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>"""
            data = {}
            past_date = date.today() - timedelta(days=7)
            interviews = Interview.objects.filter(status='feedback_due', start_time__date__lte=past_date)
            for interview in interviews:
                user = interview.submission.created_by
                if user.id in data.keys():
                    ids = data[user.id]["ids"] + [str(interview.id)]
                    data[user.id] = {"name": user.employee_name, "count": data.get(user.id)["count"] + 1, "ids": ids}
                else:
                    data[user.id] = {"name": user.employee_name, "count": 1, "ids": [str(interview.id)]}
            for key, value in data.items():
                count_interviews += 1
                interview_text += f"""<tr>
                                <td style="padding:5px 8px 5px 8px;">{count_interviews}</td>
                                <td style="padding:5px 8px 5px 8px;">{value['name']}</td>
                                <td style="padding:5px 8px 5px 8px;">{", ".join(value['ids'])}</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{value['count']}</td>
                            </tr>\n"""
                if count_interviews % 50 == 0:
                    data = {
                        "title": f"Count Feedback Due status Interviews till {past_date}",
                        "text": f"""<table border='2' style='border-collapse:collapse'>{interview_text}</table>"""
                    }
                    res, msg = post_msg_using_webhook(config.loud_speakers_url, data)
                    if msg == 'error':
                        raise Exception(res)
                    interview_text = f""" <tr>
                                            <th style="padding:5px 8px 5px 8px;">#</th>
                                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                                            <th style="padding:5px 8px 5px 8px;">Interview Ids</th>
                                            <th style="padding:5px 8px 5px 8px;">Count</th>
                                        </tr>"""

            data = {}
            tests = Test.objects.filter(status='feedback_due', submit_date__date__lte=past_date)
            for test in tests:
                user = test.submission.created_by
                if user.id in data.keys():
                    ids = data[user.id]["ids"] + [str(test.id)]
                    data[user.id] = {"name": user.employee_name, "count": data.get(user.id)["count"] + 1, "ids": ids}
                else:
                    data[user.id] = {"name": user.employee_name, "count": 1, "ids": [str(test.id)]}

            for key, value in data.items():
                count_tests += 1
                test_text += f"""<tr>
                                <td style="padding:5px 8px 5px 8px;">{count_tests}</td>
                                <td style="padding:5px 8px 5px 8px;">{value['name']}</td>
                                <td style="padding:5px 8px 5px 8px;">{", ".join(value['ids'])}</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{value['count']}</td>
                            </tr>\n"""
                if count_tests % 50 == 0:
                    data = {
                        "title": f"Count of Feedback due Test till {past_date}",
                        "text": f"""<table border='2' style='border-collapse:collapse'>{test_text}</table>"""
                    }
                    res, msg = post_msg_using_webhook(config.loud_speakers_url, data)
                    if msg == 'error':
                        raise Exception(res)
                    test_text = f""" <tr>
                                        <th style="padding:5px 8px 5px 8px;">#</th>
                                        <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                                        <th style="padding:5px 8px 5px 8px;">Interview Ids</th>
                                        <th style="padding:5px 8px 5px 8px;">Count</th>
                                    </tr>"""

            if count_interviews % 50 != 0:
                interview_data = {
                    "title": f"Count Feedback Due status Interviews till {past_date}",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{interview_text}</table>"""
                }
                res, msg = post_msg_using_webhook(config.loud_speakers_url, interview_data)
                if msg == 'error':
                    raise Exception(res)
            if count_tests % 50 != 0:
                test_data = {
                    "title": f"Count of Feedback due Test till {past_date}",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{test_text}</table>"""
                }
                res1, msg1 = post_msg_using_webhook(config.loud_speakers_url, test_data)
                if msg1 == 'error':
                    raise Exception(res1)

            interviews = Interview.objects.filter(
                coding_present=None, guest_type__in=['coder', 'assistance', 'assigned']
            ).exclude(status__in=['cancelled', 'scheduled', 'rescheduled'])

            coder_text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Interview ID</th>
                            <th style="padding:5px 8px 5px 8px;">Start Time</th>
                            <th style="padding:5px 8px 5px 8px;">Coders</th>
                        </tr>"""

            for interview in interviews:
                count_coder = count_coder + 1
                guest = ", ".join(interview.guest.filter(role__name='engineer').values_list('employee_name', flat=True))
                coder_text += f"""<tr>
                            <td style="padding:5px 8px 5px 8px;">{count_coder}</td>
                            <td style="padding:5px 8px 5px 8px;">{interview.id}</td>
                            <td style="padding:5px 8px 5px 8px;">{str(interview.start_time).replace('+00:00', '')}</td>
                            <td style="text-align: center;padding:5px 8px 5px 8px;">{guest}</td>
                            </tr>\n"""
                if count_coder % 50 == 0:
                    data = {
                        "title": "Interview Coders feedback due",
                        "text": f"""<table border='2' style='border-collapse:collapse'>{coder_text}</table>"""
                    }
                    res, msg = post_msg_using_webhook(config.engineering_url, data)
                    if msg == 'error':
                        raise Exception(res)
                    coder_text = f""" <tr>
                                    <th style="padding:5px 8px 5px 8px;">#</th>
                                    <th style="padding:5px 8px 5px 8px;">Interview ID</th>
                                    <th style="padding:5px 8px 5px 8px;">Coders</th>
                                </tr>"""
            if count_coder % 50 != 0:
                coder_data = {
                    "title": "Interview Coders feedback due",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{coder_text}</table>"""
                }
                res1, msg1 = post_msg_using_webhook(config.engineering_url, coder_data)
                if msg1 == 'error':
                    raise Exception(res1)
        except Exception as error:
            write_exception(message=error)
            create_cron_error(job, error)
