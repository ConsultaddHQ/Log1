from datetime import datetime
from django.db.models import F
from marketing.models import Test, Answer
from django.core.management import BaseCommand
from engineering.models import Cycle, EngineerPoint

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
           tests = Test.objects.filter(engineer_feedback__created__lte='2023-06-30',
                          engineer_feedback__created__gte='2023-01-01').order_by(F('created').asc()).distinct()
           for test in tests:
               self.assigned_test_points(test)
           print("Done")
        except Exception as error:
            print(error)
    def assigned_test_points(self, test):
        try:
            platform_name = None
            mcqs, coding_answers = 0, 0
            online_test = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                question__title='Select type of test',
                                                question__form_name='online_test').first()
            if not online_test:
                test_type = 'offline'
            else:
                test_type = 'online'
                platform = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                 question__title='Platform',
                                                 question__form_name='online_test').first()
                if platform:
                    platform_name = platform.answer
            MCQ_question_answer = Answer.objects.filter(
                object_id=test.id, content_type__model='test', question__title='Number of MCQ questions'
            ).first()
            if MCQ_question_answer:
                mcqs = MCQ_question_answer.answer

            coding_question_answer = Answer.objects.filter(
                object_id=test.id, content_type__model='test', question__title='Number of coding questions'
            ).first()
            if coding_question_answer:
                coding_answers = coding_question_answer.answer
            employee_associated = test.engineer.all()
            points = self.calculate_points(
                test_type=test_type,
                test_current_status=test.status,
                test_platform_name=platform_name,
                no_mcq_q=mcqs, no_coding_q=coding_answers,
                no_of_people_involved=len(employee_associated)
            )
            for engineer in employee_associated:
                answers = test.engineer_feedback.all()
                answer = answers.filter(question__title="Upload Documents").first()
                if 1 <= answer.created.month <= 6:
                    cycle_start = datetime(answer.created.year, 1, 1)
                    cycle_end = datetime(answer.created.year, 6, 30)
                else:
                    cycle_start = datetime(answer.created.year, 7, 1)
                    cycle_end = datetime(answer.created.year, 12, 31)
                cycle = Cycle.objects.get_or_create(start_date=cycle_start, end_date=cycle_end)
                previous_points = EngineerPoint.objects.filter(engineer=engineer, is_active=True)
                engineer_point, created = EngineerPoint.objects.get_or_create(engineer=engineer, cycle=cycle[0])
                if created:
                    previous_points.update(is_active=False)
                engineer_point.points = engineer_point.points + points
                engineer_point.save()
        except Exception as error:
            print(error)
    @staticmethod
    def calculate_mcq_points(no_of_mcq):
        first_twenty_points = (20 if no_of_mcq > 20 else no_of_mcq) * 0.25
        next_ten_points = (10 if no_of_mcq > 30 else no_of_mcq - 20) * 0.20
        rest_all_points = (no_of_mcq - 30 if no_of_mcq > 30 else -1) * 0.15
        points = first_twenty_points + (next_ten_points if next_ten_points > 0 else 0) + (
            rest_all_points if rest_all_points > 0 else 0)
        return round(points, 2)
    def calculate_points(self, test_platform_name, test_type, test_current_status,
                         no_of_people_involved=0, no_mcq_q=0, no_coding_q=0):
        points = 0
        if test_type.lower() == 'online':
            if no_mcq_q and no_coding_q:
                test_points = self.calculate_mcq_points(int(no_mcq_q)) + int(no_coding_q) * 3
                bonus_points = 0.75 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            elif no_coding_q:
                test_points = int(no_coding_q) * 3
                bonus_points = 1 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            elif no_mcq_q:
                test_points = self.calculate_mcq_points(int(no_mcq_q))
                bonus_points = 0.5 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            else:
                pass
        elif test_type.lower() == 'offline':
            test_points = 5
            bonus_points = 2 * (1 if test_current_status == 'passed' else 0)
            points = (test_points + bonus_points) / no_of_people_involved
        else:
            pass
        return round(points, 2)