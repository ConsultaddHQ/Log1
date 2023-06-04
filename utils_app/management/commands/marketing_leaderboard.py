from datetime import date, datetime

from constance import config
from django.core.management import BaseCommand

from employee.models import User
from project.models import Project
from marketing.models import Submission, Interview
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_object, create_cron_error


class Command(BaseCommand):

    @staticmethod
    def get_leaders(payload, category_data, positions, category_rely_data=None):
        prev_score, prev_id = None, None
        count = 1
        category = list(category_data.keys())[0]
        employee_scores = category_data[category]
        sorted_data = dict(sorted(employee_scores.items(), key=lambda x: x[1], reverse=True))
        for data in sorted_data:
            employee_id = data
            if count > positions:
                break
            if not sorted_data.get(data) and prev_score and prev_id:
                employee_score = prev_score
                employee_id = prev_id
            else:
                employee_score = sorted_data[data]

            same_score_employees = list(filter(lambda k: sorted_data[k] == employee_score, sorted_data.keys()))
            if len(same_score_employees) > 1 and category_rely_data:
                employee_rely_score = dict((k, category_rely_data[k]) for k in category_rely_data if k in same_score_employees)
                sorted_employee_rely_score = dict(sorted(employee_rely_score.items(), key=lambda x: x[1], reverse=True))
                employee_id = list(sorted_employee_rely_score.keys())[0]

            employee = User.objects.get(employee_id=employee_id)
            emp_data = {
                "name": f"<@{employee.slack_id}>" if employee.slack_id else employee.employee_name,
                "team": employee.team.name, "score": sorted_data[employee_id]
            }
            if employee_id != data:
                prev_score = sorted_data[employee_id]
                prev_id = data
            payload[count][category] = emp_data
            sorted_data = {k: v for k, v in sorted_data.items() if k != employee_id}
            count += 1

        return payload

    def handle(self, *args, **options):
        job = create_cron_object(name='Marketing Leaderboard')

        try:
            positions = 2
            leaders_data = {
                "positions": positions, "data": {}, "categories": ['offer', 'interview', 'submission']
            }
            for rank in range(1, positions+1):
                leaders_data["data"][rank] = {}
            leaders_data['competition_day'] = str(
                date.today() - datetime.strptime('2023-05-14', "%Y-%m-%d").date()).split(' ')[0]

            sub_info = {"submission": {}}
            submission_score = sub_info['submission']
            submissions = Submission.objects.filter(created__gte='2023-05-15')
            for sub in submissions:
                employee_id = sub.created_by.employee_id
                if employee_id not in submission_score:
                    submission_score[employee_id] = 1
                else:
                    submission_score[employee_id] = submission_score[employee_id] + 1
            leaders_data["data"] = self.get_leaders(leaders_data["data"], sub_info, positions)

            interview_info = {'interview': {}}
            interview_score = interview_info['interview']
            interviews = Interview.objects.filter(
                submission__in=submissions, status__in=['next_round', 'failed', 'offer', 'feedback_due']
            )
            for interview in interviews:
                employee_id = interview.submission.created_by.employee_id
                if employee_id not in interview_score:
                    interview_score[employee_id] = 1
                else:
                    interview_score[employee_id] = interview_score[employee_id] + 1
            leaders_data["data"] = self.get_leaders(leaders_data["data"], interview_info, positions, submission_score)

            offer_info = {'offer': {}}
            offer_score = offer_info['offer']
            offers = Project.objects.filter(
                submission__in=submissions, statuses__status__in=['on_boarded', 'joined'], statuses__is_current=True
            )
            for offer in offers:
                employee_id = offer.submission.created_by.employee_id
                if employee_id not in offer_info:
                    offer_score[employee_id] = 1
                else:
                    offer_score[employee_id] = offer_score[employee_id] + 1

            leaders_data["data"] = self.get_leaders(leaders_data["data"], offer_info, positions, interview_score)

            MessageCard.marketing_leaderboard(leaders_data, config.slack_consultadd_compete_url)
        except Exception as error:
            print(error)
            create_cron_error(job, error)
