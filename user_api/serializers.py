from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from project.models import Project
from user_api.models import UserAPIKey
from consultant.models import Consultant
from marketing.models import Submission, Interview, Lead, VendorCompany, VendorContact


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"  # Allow clients to set page size
    max_page_size = 100  # Limit the maximum page size

    def get_paginated_response(self, data):
        return Response({
            "links": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "count": self.page.paginator.count,
            "page_size": self.page.paginator.per_page,
            "current_page": self.page.number,
            "results": data,
        })


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


class ConsultantDetailsSerializer(serializers.ModelSerializer):
    active_projects = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ["id", "name", "email", "rate", "active_projects"]

    @staticmethod
    def get_active_projects(obj):
        active_projects = Project.objects.filter(
            submission__consultant_marketing__consultant=obj,
            statuses__status="joined", statuses__is_current=True
        ).values("id", "submission_id", "employer", "created")

        return [
            {
                "project_id": po.get("id"),
                "employer": po.get("employer"),
                "submission_id": po.get("submission_id"),
                "created": po.get("created").strftime("%Y-%m-%d"),
            }
            for po in active_projects
        ]


class InterviewDetailsSerializer(serializers.ModelSerializer):
    round = serializers.SerializerMethodField()
    status = serializers.CharField(source="get_status_display")
    screening_type = serializers.CharField(source="get_screening_type_display")
    interview_mode = serializers.CharField(source="get_interview_mode_display")
    call_type = serializers.CharField(source="call_type.display_name", default=None)
    supervisor = serializers.SerializerMethodField(source="supervisor.employee_name", default=None)

    class Meta:
        model = Interview
        fields = [
            "id", "feedback", "end_time", "start_time", "call_type", "supervisor",
            "screening_type", "round", "interview_mode", "status"
        ]

    @staticmethod
    def get_round(obj):
        return f"Round - {obj.round}"

    @staticmethod
    def get_supervisor(obj):
        return obj.supervisor.employee_name


class ProjectDetailsSerializer(serializers.ModelSerializer):
    end_date = serializers.DateField(format="%Y-%m-%d")
    start_date = serializers.DateField(format="%Y-%m-%d")
    submission = serializers.IntegerField(source="submission_id")
    remote_consultant_id = serializers.IntegerField(source="consultant_id")

    class Meta:
        model = Project
        fields = [
            "id", "rate", "start_date", "end_date", "feedback", "employer", "created",
            "is_remote", "city", "duration", "submission", "remote_consultant_id", "status"
        ]


class LeadSerializer(serializers.ModelSerializer):
    position = serializers.CharField(source="position.display_name", required=False)

    class Meta:
        model = Lead
        ref_name = 'UserApiLead'
        fields = ["id", "position"]


class VendorCompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = VendorCompany
        ref_name = 'UserApiVendorCompany'
        fields = ["id", "name", "created_by"]


class VendorContactSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.employee_name")

    class Meta:
        model = VendorContact
        ref_name = 'UserApiVendorContact'
        fields = ["id", "created_by", "company_id", "source_link", "email", "region", "name"]


class MarketingTriggerSerializer(serializers.ModelSerializer):
    lead = LeadSerializer(read_only=True)
    created_by = serializers.SerializerMethodField()
    project_details = serializers.SerializerMethodField()
    interview_details = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer(read_only=True)
    vendor_company = VendorCompanySerializer(source="vendor", read_only=True)
    work_type = serializers.CharField(source="get_work_type_display", read_only=True)
    marketing_team = serializers.CharField(source="marketing_team.name", read_only=True)
    consultant_details = ConsultantDetailsSerializer(source="consultant", read_only=True)
    submission_status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "client", "email", "work_type", "marketing_team", "submission_status", "created", "modified",
            "rate", "employer", "created_by", "vendor_company", "vendor_contact", "lead", "consultant_details",
            "interview_details", "project_details"
        ]

    def get_project_details(self, obj):
        project = getattr(obj, "project", None)
        if project:
            return ProjectDetailsSerializer(project).data
        return {}

    def get_interview_details(self, obj):
        if not hasattr(obj, "screening"):
            return []
        return InterviewDetailsSerializer(obj.screening.filter().order_by("-id"), many=True).data

    @staticmethod
    def get_created_by(obj):
        creator = obj.created_by
        return {
            "id": creator.id, "name": creator.employee_name, "team": creator.team.name
        } if creator else {}
