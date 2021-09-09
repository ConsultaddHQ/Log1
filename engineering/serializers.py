from rest_framework import serializers

from employee.models import User
from project.models import Project, ProjectSupport, SupportStatus


class POCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email')


class EngineeringSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'support', 'start_date', 'submission', 'status')

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_support(obj):
        data = []
        for support in obj.support.all():
            data.append({
                "email": support.support.email,
                "name": support.support.employee_name,
            })
        return data

    @staticmethod
    def get_submission(obj):
        lead = obj.submission.lead
        return {
            "location": lead.city,
            "job_title": lead.job_title,
            "client": obj.submission.client,
            "vendor": lead.vendor_company.name,
        }

    @staticmethod
    def get_consultant(obj):
        consultant = obj.submission.consultant_marketing.consultant
        return {
            'id': consultant.id,
            'name': consultant.name,
            'email': consultant.email,
        }


class EngineeringDetailSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    remote_consultant = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'start_date', 'submission', 'status', 'remote_consultant',
                  'marketer')

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_marketer(obj):
        marketer = obj.submission.created_by
        return {
            "id": marketer.id,
            "email": marketer.email,
            "name": marketer.employee_name,
        }

    @staticmethod
    def get_submission(obj):
        lead = obj.submission.lead
        return {
            "location": lead.city,
            "job_title": lead.job_title,
            "client": obj.submission.client,
            "vendor": lead.vendor_company.name,
        }

    @staticmethod
    def get_consultant(obj):
        recruiter, retention = None, None
        consultant = obj.submission.consultant_marketing.consultant
        qs = consultant.pocs.filter(poc_type='recruiter', end=None)
        if qs:
            recruiter = POCSerializer(qs.first().poc).data
        qs = consultant.pocs.filter(poc_type='retention', end=None)
        if qs:
            retention = POCSerializer(qs.first().poc).data

        return {
            'id': consultant.id,
            'recruiter': recruiter,
            'retention': retention,
            'name': consultant.name,
            'email': consultant.email,
        }

    @staticmethod
    def get_remote_consultant(obj):
        return {
            'id': obj.consultant.id,
            'name': obj.consultant.name,
            'email': obj.consultant.email,
        }


class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email')


class SupportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportStatus
        fields = ('id', 'frequency', 'change_date')


class ProjectSupportSerializer(serializers.ModelSerializer):
    support = SupportSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = ('id', 'start', 'end', 'feedback', 'support', 'status')

    @staticmethod
    def get_status(obj):
        return SupportStatusSerializer(obj.statuses.filter(is_current=True).first()).data
