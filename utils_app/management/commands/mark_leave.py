import csv
from django.db.models import Q
from datetime import datetime, date, timedelta

from django.core.management import BaseCommand

from consultant.models import Consultant
from project.models import ConsultantLeave, Leave
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


DURATION_TYPES = {'hourly': 'hours', 'half': 4, 'full': 8}


class Command(BaseCommand):

    @staticmethod
    def validate_dates(from_date_obj, to_date_obj):
        """

        :rtype: object
        """
        try:
            current_date_obj = date.today()
        except ValueError:
            return "Invalid date format: Dates should be in YYYY-MM-DD format.", 400

        # Ensure 'from_date' is before or equal to 'to_date'
        if from_date_obj > to_date_obj:
            return "Invalid input: 'from_date' cannot be after 'to_date'.", 400

        # Determine the leave year and the cutoff date for previous year's leave
        leave_year = from_date_obj.year
        cutoff_date = date(leave_year + 1, 1, 30)

        # Validation conditions
        if from_date_obj.year != to_date_obj.year:
            return "Leave cannot span multiple calendar years.", 400

        if current_date_obj <= cutoff_date and leave_year == current_date_obj.year - 1:
            return "Leave application for the previous year is allowed.", 200

        if leave_year == current_date_obj.year:
            return "Leave application for the current year is allowed.", 200

        return "Leave validity has expired", 400

    @staticmethod
    def calculate_leave_hours(start_date, end_date):
        total_days=0
        while end_date >= start_date:
            if start_date.weekday() < 5:
                total_days += 1
            start_date = start_date + timedelta(days=1)
        return total_days * 8

    def handle(self, *args, **options):
        try:
            # file = open("Leave requests 2024_2025 - Sheet2.csv", "r")
            # w_file = open("duplicate_leave.csv", "w+")
            # writer = csv.writer(w_file)
            # writer.writerow(["Consultant Name", "Email", "to_date", "from_date", "Leave Type", "Duration", "Count", "Leave ID"])
            # reader = csv.reader(file)
            # count = 0
            # for row in reader:
            #     if count == 0:
            #         count+=1
            #         continue
            #     con_obj = Consultant.objects.get(email=row[1])
            #     to_date_object = datetime.strptime(row[4], "%m.%d.%y").date()
            #     from_date_object = datetime.strptime(row[3], "%m.%d.%y").date()
            #     if row[2] == 'PTO':
            #         leave_type = "pto"
            #     else:
            #         leave_type = "sick_leave"
            #
            #     leave_qs = Leave.objects.filter(
            #         to_date=to_date_object, from_date=from_date_object,
            #         leave_type__leave_type__name=leave_type, status='approved', consultant=con_obj
            #     ).order_by('created')
            #     count=1
            #     for obj in leave_qs:
            #         if count > 1:
            #             writer.writerow([
            #                 obj.consultant.name, obj.consultant.email, obj.to_date.strftime("%Y-%m-%d"),
            #                 obj.from_date.strftime("%Y-%m-%d"), obj.leave_type.leave_type.name, obj.total_hours, count,obj.id, obj.created
            #             ])
            #             obj.leave_type.balance+=float(obj.total_hours)
            #             obj.leave_type.save()
            #             obj.delete()
            #         count+=1
                # _valid, status = self.validate_dates(from_date_object, to_date_object)
                # if status != 200:
                #     print("Invalid dates")
                #     break
                #
                # if row[2] == 'PTO':
                #     leave_type = "pto"
                # else:
                #     leave_type = "sick_leave"
                #
                # consultant_leave_obj = ConsultantLeave.objects.get(
                #     consultant=con_obj, leave_type__name=leave_type, year=from_date_object.year
                # )
                # if row[5]:
                #     leave_hours = float(row[5][0])
                # else:
                #     leave_hours = self.calculate_leave_hours(from_date_object, to_date_object)
                #
                # if float(leave_hours) > consultant_leave_obj.balance:
                #     print("Insufficient balance")
                #
                # leave = Leave.objects.create(
                #     leave_type=consultant_leave_obj,
                #     consultant=con_obj,
                #     applied_on=date.today(),
                #     total_hours=leave_hours,
                #     to_date=to_date_object,
                #     from_date=from_date_object,
                #     description="Leave Applied through Admin",
                #     status='approved'
                # )
                # consultant_leave_obj.balance -= leave_hours
                # consultant_leave_obj.save()
            file = open("issue_leave.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Consultant Name", "Email", "Leave Type", "From", "To", "Duration Mentioned", "Actual Duration"
            ])
            leave_qs = Leave.objects.filter(leave_type__year=2024, status='approved').filter(
                Q(total_hours=None) | Q(total_hours=0.0)
            )
            for obj in leave_qs:
                if obj.from_date.year == 2025:
                    actual_duration = float(self.calculate_leave_hours(obj.from_date, obj.to_date))
                    consultant_leave_obj = ConsultantLeave.objects.get(
                        year=obj.from_date.year, consultant=obj.consultant, leave_type=obj.leave_type.leave_type
                    )
                    obj.leave_type = consultant_leave_obj
                    obj.total_hours = float(self.calculate_leave_hours(obj.from_date, obj.to_date))
                    consultant_leave_obj.balance -= actual_duration

                    # obj.save()
                    # consultant_leave_obj.save()

                    writer.writerow([
                        obj.consultant.name, obj.consultant.email, obj.leave_type.leave_type.name, obj.from_date,
                        obj.to_date, obj.total_hours, self.calculate_leave_hours(obj.from_date, obj.to_date)
                    ])
            print(leave_qs.count())
        except Exception as error:
            print(error)
