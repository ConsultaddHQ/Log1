from datetime import date
from rest_framework import serializers

from employee.models import User
from attachment.models import Attachment
from attachment.serializers import AttachmentGetSerializer
from project.models import Project, SupportStatus, TimeSheet
from engineering.models import ProjectDescription, ProjectUpdate


class POCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email')


class EngineeringSerializer(serializers.ModelSerializer):
    project_status = serializers.SerializerMethodField()
    support_status = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'support', 'start_date', 'submission', 'project_status', 'support_status')

    @staticmethod
    def get_project_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().get_status_display()
        return None

    @staticmethod
    def get_support_status(obj):
        if obj.statuses.filter(status__istartswith='terminated').first():
            return 'terminated'

        support_qs = obj.support.filter(end=None)
        if support_qs:
            qs = support_qs.first().statuses.filter(is_current=True)
            if qs:
                support_status = qs.first()
                if obj.start_date > date.today():
                    return "Training"
                elif support_status.frequency == 'more_than_2_days':
                    return "Active"
                elif support_status.frequency == 'less_than_3_days':
                    return "Less Active"
                elif support_status.frequency in ('twice_a_month', 'independent'):
                    return "Independent"
                else:
                    return None
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
    marketer = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    remote_consultant = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'start_date', 'submission', 'remote_consultant', 'marketer')

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
        resume = None
        qs = obj.submission.attachments.filter(attachment_type='resume')
        if qs:
            resume = qs.first()
            resume = {
                "id": resume.id,
                "name": resume.attachment_file.name,
            }
        return {
            "resume": resume,
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


class TimesheetSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'attachments', 'remark', 'con_comment')

    @staticmethod
    def get_start(obj):
        return obj.start.strftime("%m/%d/%Y")

    @staticmethod
    def get_end(obj):
        return obj.end.strftime("%m/%d/%Y")

    @staticmethod
    def get_attachments(obj):
        return AttachmentGetSerializer(obj.attachments.all(), many=True).data


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectUpdate
        fields = '__all__'


class ProjectUpdateGetSerializer(serializers.ModelSerializer):
    update_by = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUpdate
        exclude = ('project',)

    @staticmethod
    def get_update_by(obj):
        return {
            "id": obj.update_by.id,
            "email": obj.update_by.email,
            "name": obj.update_by.employee_name,
        }

    @staticmethod
    def get_tagged_user(obj):
        data = []
        if obj.tagged_user.exists():
            for user in obj.tagged_user.first().tagged_user.all():
                data.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.employee_name,
                })
        return data

    @staticmethod
    def get_attachments(obj):
        attachment = Attachment.objects.filter(object_id=obj.id, content_type__model="projectupdate")
        return AttachmentGetSerializer(attachment, many=True).data


class ProjectDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDescription
        fields = '__all__'
