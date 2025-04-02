from rest_framework import serializers

from project.models import Project
from user_api.models import UserAPIKey
from marketing.models import Submission


class UserApiSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    api_key = serializers.SerializerMethodField()

    class Meta:
        model = UserAPIKey
        fields = ('id', 'user', 'api_key')

    @staticmethod
    def get_user(obj):
        return {
            "user_id": obj.user_id,
            "name": obj.user.employee_name
        }

    @staticmethod
    def get_api_key(obj):
        return {
            "api_key": obj.api_key.api_key,
            "name": obj.api_key.name,
            "id": obj.api_key.id
        }


class MarketingTriggerSerializer(serializers.ModelSerializer):
    lead = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    vendor_company = serializers.SerializerMethodField()
    vendor_contact = serializers.SerializerMethodField()
    marketing_team = serializers.SerializerMethodField()
    project_details = serializers.SerializerMethodField()
    submission_status = serializers.SerializerMethodField()
    interview_details = serializers.SerializerMethodField()
    consultant_details = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "client", "email", "work_type", "vendor_company", "vendor_contact", "created_by", "rate", "employer",
            "lead", "consultant_details", "project_details", "interview_details", "marketing_team", "submission_status"
        ]

    @staticmethod
    def get_vendor_company(obj):
        return {
            "id": obj.vendor.id, "name": obj.vendor.name, "created_by": obj.vendor.created_by,
        }

    @staticmethod
    def get_lead(obj):
        lead = obj.lead
        return {
            "lead_id": lead.id, "job_position": lead.job_title
        }

    @staticmethod
    def get_vendor_contact(obj):
        return {
            "id": obj.vendor_contact.id, "created_by": obj.vendor_contact.created_by.employee_name,
            "vendor_company_id": obj.vendor_contact.company_id, "source_link": obj.vendor_contact.source_link,
            "email": obj.vendor_contact.email, "region": obj.vendor_contact.region, "name": obj.vendor_contact.name
        }

    @staticmethod
    def get_project_details(obj):
        if hasattr(obj, 'project'):
            project_obj = obj.project
            return {
                "id": project_obj.id, "rate": project_obj.rate,
                "start_date": project_obj.start_date.strftime("%Y-%m-%d"),
                "end_date": project_obj.end_date.strftime("%Y-%m-%d"),
                "feedback": project_obj.feedback, "employer": project_obj.employer,
                "is_remote": project_obj.is_remote, "city": project_obj.city, "duration": project_obj.duration,
                "submission": project_obj.submission_id, "remote_consultant_id": project_obj.consultant_id,
                "status": project_obj.status
            }
        return dict()

    @staticmethod
    def get_interview_details(obj):
        screenings = list()
        if hasattr(obj, 'screening'):
            screening_qs = obj.screening.all()
            for screening in screening_qs:
                screenings.append({
                    "id": screening.id,
                    "feedback": screening.feedback,
                    "end_time": screening.end_time.strftime("%Y-%m-%d"),
                    "start_time": screening.start_time.strftime("%Y-%m-%d"),
                    "call_type": screening.call_type.display_name if screening.call_type else None,
                    "screening_type": screening.get_screening_type_display(), "Round": f"Round - {screening.round}",
                    "interview_mode": screening.get_interview_mode_display(), "status": screening.get_status_display(),
                    "supervisor": screening.supervisor.employee_name
                    if screening.supervisor.employee_id != 9999 else "Consultant"
                })
        return screenings

    @staticmethod
    def get_submission_status(obj):
        return obj.get_status_display()

    @staticmethod
    def get_marketing_team(obj):
        return obj.marketing_team.name

    @staticmethod
    def get_created_by(obj):
        return {
            "id": obj.created_by.id, "name": obj.created_by.employee_name, "team": obj.created_by.team.name
        }

    @staticmethod
    def get_consultant_details(obj):
        active_project_qs = Project.objects.filter(
            submission__consultant_marketing__consultant=obj.consultant, created__gt="2024-12-31",
            statuses__status='joined', statuses__is_current=True
        )
        active_projects = [
            {
                "project_id": po.id, "submission_id": po.submission.id,
                "employer": po.employer, "created_at": po.created.strftime("%Y-%m-%d")
            } for po in active_project_qs
        ]
        return {
            "id": obj.consultant.id, "name": obj.consultant.name,
            "email": obj.consultant.email, "active_projects": active_projects
        }
