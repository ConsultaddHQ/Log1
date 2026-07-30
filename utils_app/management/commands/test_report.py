import csv
from django.core.management import BaseCommand

from marketing.models import Test, Answer


class Command(BaseCommand):

    @staticmethod
    def get_ratio(count, total):
        ratio = round(count/total, 3)*100
        return ratio

    def handle(self, *args, **options):
        try:
            data = {}
            file = open("Test Report.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Engineer Name", "Total Test", "Feedback Pending", "Online test", "Offline Test", "Passed Test",
                "Total Passed/Failed Test", "Success Ratio", "Failed Test", "Failure Ratio", "Involved Test IDs"
            ])
            queryset = Test.objects.filter(created__gte='2024-01-01', created__lt='2024-02-01').exclude(status='cancelled')
            ans_qs = Answer.objects.filter(question__title="Select type of test")
            for obj in queryset:
                engineers = obj.engineer.all()
                for eng in engineers:
                    ans = ans_qs.filter(object_id=obj.id, content_type__model='test').first()
                    if ans.answer == "online":
                        is_offline = False
                    else:
                        is_offline = True
                    if eng.employee_id not in data:
                        data[eng.employee_id] = {
                            "name": eng.employee_name,
                            "tests": [obj.id], "total_test": 1,
                            "offline_test": 1 if is_offline else 0,
                            "online_test": 1 if not is_offline else 0,
                            "passed_count": 1 if obj.status == 'passed' else 0,
                            "failure_count": 1 if obj.status == 'failed' else 0,
                            "feedback_due": 1 if obj.status == 'feedback_due' else 0,
                            "total_test_P/F": 1 if obj.status in ['passed', 'failed'] else 0
                        }
                    else:
                        data[eng.employee_id]["total_test"] += 1
                        data[eng.employee_id]["tests"].append(obj.id)
                        if obj.status == 'passed':
                            data[eng.employee_id]["total_test_P/F"] += 1
                            data[eng.employee_id]["passed_count"] += 1
                        elif obj.status == 'failed':
                            data[eng.employee_id]["total_test_P/F"] += 1
                            data[eng.employee_id]["failure_count"] += 1
                        elif obj.status == 'feedback_due':
                            data[eng.employee_id]["feedback_due"] += 1

                        if is_offline:
                            data[eng.employee_id]["offline_test"] += 1
                        else:
                            data[eng.employee_id]["online_test"] += 1

            for key in data.keys():
                writer.writerow([
                    data[key]["name"], data[key]["total_test"], data[key]["feedback_due"],
                    data[key]["online_test"], data[key]["offline_test"], data[key]["total_test_P/F"],
                    data[key]["passed_count"], self.get_ratio(data[key]["passed_count"], data[key]["total_test_P/F"]),
                    data[key]["failure_count"], self.get_ratio(data[key]["failure_count"], data[key]["total_test_P/F"]),
                    data[key]["tests"],
                ])
        except Exception as error:
            print(error)
