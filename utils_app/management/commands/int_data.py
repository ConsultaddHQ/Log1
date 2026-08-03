import csv
from constance import config
from django.core.management import BaseCommand

from marketing.models import Interview


class Command(BaseCommand):

    @staticmethod
    def get_str_from_dict(key_value):
        value_str = ""
        for key in key_value.keys():
            value_str += f"{key}->{key_value.get(key)}\n"
        return value_str

    @staticmethod
    def get_interviewer_details(obj):
        details = {"name": list(), "email": list(), "linkedin": list()}
        interviewers = obj.interviewers.all()
        for interviewer in interviewers:
            if interviewer.name:
                details["name"].append(interviewer.name)
            if interviewer.email:
                details["email"].append(interviewer.email)
            if interviewer.linkedin:
                details["linkedin"].append(interviewer.linkedin)
        return details

    def handle(self, *args, **options):
        try:
            data = {}
            file = open("Interview Report.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Consultant Name", "Client Name", "Vendor Name", "Position", "Final Status",
                "Total Rounds", "Interviewer Name", "Interviewer Email", "Interviewer Linkedin"
            ])
            queryset = Interview.objects.filter(
                start_time__date__gte="2024-05-01", start_time__date__lt="2024-08-01", screening_type='interview'
            )
            for obj in queryset:
                sub = obj.submission

                interviewer_details = self.get_interviewer_details(obj)
                if sub not in data:
                    if obj.call_type:
                        call_type = obj.call_type.display_name
                    else:
                        call_type = "Supervisor" if obj.supervisor.employee_id != 9999 else "Consultant"
                    data[sub] = {
                        "call_type": {f"Round {obj.round}": call_type},
                        "total_round": 1, "supervisors": {f"Round {obj.round}": obj.supervisor.employee_name},
                        "round_status": {f"Round {obj.round}": obj.get_status_display()},
                        "interviewers_name": ", ".join(interviewer_details.get("name")),
                        "interviewers_email": ", ".join(interviewer_details.get("email")),
                        "interviewers_linkedin": ", ".join(interviewer_details.get("linkedin")),
                    }
                else:
                    data[sub]["total_round"] += 1
                    if obj.call_type:
                        data[sub]["call_type"][f"Round {obj.round}"] = obj.call_type.display_name
                    else:
                        data[sub]["call_type"][f"Round {obj.round}"] = "Supervisor" if obj.supervisor.employee_id != 9999 else "Consultant"
                    data[sub]["interviewers_name"] = ", ".join(interviewer_details.get("name"))
                    data[sub]["interviewers_email"] = ", ".join(interviewer_details.get("email"))
                    data[sub]["interviewers_linkedin"] = ", ".join(interviewer_details.get("linkedin"))
                    data[sub]["round_status"][f"Round {obj.round}"] = obj.get_status_display()
                    data[sub]["supervisors"][f"Round {obj.round}"] = obj.supervisor.employee_name

            for key in data.keys():
                # roundwise_status = self.get_str_from_dict(data[key]["round_status"])
                final_status_obj = key.screening.filter(
                    screening_type='interview', start_time__date__gte="2024-05-01", start_time__date__lt="2024-08-01"
                ).order_by('-round').first()
                final_status = final_status_obj.get_status_display() if final_status_obj else "NA"
                position = key.lead.position.display_name if key.lead.position else key.lead.job_title
                writer.writerow([
                    key.consultant.name, key.client, key.vendor.name, position, final_status, data[key]["total_round"],
                    data[key]["interviewers_name"], data[key]['interviewers_email'], data[key]['interviewers_linkedin']
                ])
        except Exception as error:
            print(error)
