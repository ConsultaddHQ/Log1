import csv
from django.core.management import BaseCommand

from marketing.models import Interview, Submission


def get_sup_feedback(screener):
    supervisor_feedback_obj = screener.supervisor_feedback.filter(question__title='Remark').first()
    if supervisor_feedback_obj:
        return supervisor_feedback_obj.answer
    else:
        return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open("SubmissionData.csv", "w")
            writer = csv.writer(file)
            column = [
                "Submission ID", "Consultant Name", "Marketer Name", "Interview ID", "Scheduled At", "Supervisor Name",
                "Round Number", "Status", "Call Type", "Coder Feedback", "Supervisor Feedback", "Marketer Feedback"
            ]
            writer.writerow(column)
            submission_qs = Submission.objects.filter(
                screening__start_time__gt="2023-12-31", screening__start_time__lt="2024-06-25",
                screening__screening_type='interview'
            ).order_by("id").distinct("id")
            for submission in submission_qs:
                for screening in submission.screening.exclude(status='cancelled').filter(screening_type='interview'
                                                                                         ).order_by('id').distinct("id"):
                    writer.writerow([
                        submission.id, submission.consultant.name, submission.created_by.employee_name, screening.id,
                        screening.start_time.strftime("%d %B, %Y"), screening.supervisor.employee_name,
                        f"R-{screening.round}", screening.get_status_display(),
                        screening.call_type.display_name if screening.call_type else None, screening.guest_remark,
                        get_sup_feedback(screening), screening.feedback
                    ])
        except Exception as error:
            print(error)


# from django.core.management import BaseCommand
# from project.models import Project
#
#
# class Command(BaseCommand):
#     help = "This is one time command to move user avatar to AWS-S3 bucket"
#
#     def handle(self, *args, **options):
#         try:
#             report_schema = ['Consultant Name', 'Client Name', 'Marketer Name', 'Start Date', 'End Date',
#                              'Project Status', 'Terminated At', 'Termination Reason', 'Project Duration', 'IsRemote',
#                              'Support Person/Remote Engineer']
#             project_info = Project.objects.filter(
#                 statuses__created__range=["2024-01-01", "2024-06-25"],
#                 statuses__status__istartswith='terminated', statuses__is_current=True
#             ).exclude(submission__status='archive').order_by('id').distinct('id')
#
#             final_lst = []
#             for obj in project_info:
#                 supp_info = get_consultant_name(obj)
#                 support_person_name = obj.support.all()
#                 supp_lst, proxy_lst = [], []
#                 for row in support_person_name:
#                     if not row.is_proxy_support:
#                         supp_lst.append(row.support.employee_name)
#
#                 supp_or_remote_eng = supp_lst if not obj.is_remote else supp_info.get('remote engineer')
#                 diff = obj.end_date - obj.start_date
#                 if diff.days < 7:
#                     duration = f"{diff.days} days"
#                 else:
#                     months = int(diff.days) // 30
#                     weeks = round(int(diff.days - months * 30) // 7, 0)
#                     duration = f"{months} months, {weeks / 10} weeks"
#
#                 _data_dict = {"Consultant Name": supp_info.get('name'), "Client Name": obj.submission.client,
#                               "Marketer Name": obj.submission.created_by.employee_name,
#                               "Start Date": obj.start_date, "End Date": obj.end_date, "Project Status": obj.status,
#                               "Terminated At": obj.statuses.filter(is_current=True).first().created.strftime("%d %B, %Y"),
#                               "Termination Reason": obj.feedback, "Project Duration": duration,
#                               "IsRemote": obj.is_remote,
#                               'Support Person/Remote Engineer': supp_or_remote_eng
#                               }
#                 final_lst.append(_data_dict)
#             write_csv_file(report_schema, final_lst, 'ProjectReport.csv')
#         except Exception as error:
#             print(error)
#
#
# def write_csv_file(header, data, output_file):
#     import csv
#
#     # Writing to csv file
#     with open(output_file, 'w', newline='') as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=header)
#
#         writer.writeheader()
#
#         for row in data:
#             writer.writerow(row)
#
#
# def get_consultant_name(obj):
#     if obj.consultant:
#         name = obj.consultant.name if obj.consultant else 'Not Assigned'
#         if obj.is_remote:
#             return {
#                 "remote engineer": name, "name": f"{obj.submission.consultant.name}"
#             }
#         else:
#             return {"name": obj.submission.consultant.name, "remote engineer": name}
#     return {"name": "Not Assigned"}
