import datetime
from datetime import date
from rest_framework import serializers

from employee.models import User
from attachment.models import Attachment
from marketing.models import Test, Interview
from attachment.serializers import AttachmentGetSerializer
from project.models import Project, SupportStatus, TimeSheet, ProjectSupport
from engineering.models import ProjectDescription, ProjectUpdate, TrainingCheckList, TrainingAgenda


class POCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email')


class EngineeringSerializer(serializers.ModelSerializer):
    remark = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    support_status = serializers.SerializerMethodField()
    project_status = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'support', 'start_date', 'submission', 'project_status', 'support_status',
                  'remark', 'assignment_status')

    @staticmethod
    def get_remark(obj):
        if hasattr(obj, 'description'):
            remark = obj.description.remark
            return remark
        return None

    @staticmethod
    def get_project_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().get_status_display()
        return None

    @staticmethod
    def get_assignment_status(obj):
        if obj.created.date() < datetime.date(2021, 10, 1):
            return "Old Project"
        if obj.support.exists():
            return "Assigned"
        else:
            return "Unassigned"

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
            'location': consultant.current_city
        }

    @staticmethod
    def get_support(obj):
        data = []
        for support in obj.support.filter(end=None):
            data.append({
                "email": support.support.email,
                "name": support.support.employee_name,
            })
        if len(data) < 1:
            for support in obj.support.all():
                data.append({
                    "email": support.support.email,
                    "name": support.support.employee_name,
                })
        return data

    @staticmethod
    def get_support_status(obj):
        if obj.statuses.filter(status__istartswith='terminated').first():
            return 'terminated'

        support_qs = obj.support.filter(end=None)
        support = obj.support.all()
        if support_qs:
            qs = support_qs.first().statuses.filter(is_current=True)
            if qs:
                support_status = qs.first()
                if obj.start_date and obj.start_date >= date.today():
                    return "Training"
                elif support_status.frequency == 'more_than_2_days':
                    return "Active"
                elif support_status.frequency == 'less_than_3_days':
                    return "Less Active"
                elif support_status.frequency in ('twice_a_month', 'independent'):
                    return "Independent"
        elif support:
            qs = support.latest('start').statuses.filter(is_current=True)
            if qs:
                support_status = qs.first()
                if obj.start_date and obj.start_date >= date.today():
                    return "Training"
                elif support_status.frequency == 'more_than_2_days':
                    return "Active"
                elif support_status.frequency == 'less_than_3_days':
                    return "Less Active"
                elif support_status.frequency in ('twice_a_month', 'independent'):
                    return "Independent"
        return None


class EngineeringDetailSerializer(serializers.ModelSerializer):
    marketer = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    remote_consultant = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'start_date', 'submission', 'remote_consultant', 'marketer', 'is_remote')

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
            'location': consultant.current_city,
        }

    @staticmethod
    def get_remote_consultant(obj):
        if obj.is_remote:
            return {
                'id': obj.consultant.id,
                'name': obj.consultant.name,
                'email': obj.consultant.email,
            }
        return None


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
    blocker = serializers.SerializerMethodField()
    update_by = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUpdate
        exclude = ('project',)

    @staticmethod
    def get_blocker(obj):
        return obj.blocker.replace("<p></p>", "") if obj.blocker else obj.blocker

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


class TrainingAgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingAgenda
        fields = '__all__'


class TrainingCheckListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCheckList
        fields = '__all__'


class EngineerProjectSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    modified_at = serializers.SerializerMethodField()
    support_status = serializers.SerializerMethodField()
    support_duration = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = ('id', 'created', 'start', 'end', 'feedback', 'support_status', 'consultant', 'project', 'description',
                  'support_duration', 'modified_at')

    @staticmethod
    def get_support_status(obj):
        status = obj.statuses.filter(is_current=True).first()
        if obj.project.statuses.filter(status__istartswith='terminated').first():
            return 'Terminated'
        elif obj.project.start_date and obj.project.start_date > date.today():
            return 'Training'
        elif status:
            if status.frequency == 'more_than_2_days':
                return 'Active'
            elif status.frequency == 'less_than_3_days':
                return 'Less_Active'
            elif status.frequency in ('twice_a_month', 'independent'):
                return 'Independent'
        else:
            return None

    @staticmethod
    def get_project(obj):
        project = obj.project
        data = {
            "id": project.id,
            "status": project.status,
            "end_date": project.end_date,
            "feedback": project.feedback,
            "is_remote": project.is_remote,
            "start_date": project.start_date,
            "client": project.submission.client
        }
        return data

    @staticmethod
    def get_description(obj):
        if hasattr(obj.project, 'description'):
            data = {
                "timezone": obj.project.description.timezone,
                "technology": obj.project.description.timezone
            }
            return data
        return None

    @staticmethod
    def get_modified_at(obj):
        update = obj.project.updates.all().order_by('-created').first()
        if update:
            data = {
                "id": update.id,
                "date": update.created.date()
            }
            return data
        return None

    @staticmethod
    def get_consultant(obj):
        consultant = obj.project.consultant
        data = {
            "id": consultant.id,
            'name': consultant.name,
            'email': consultant.email,
            'contact': consultant.phone_no
        }
        return data

    @staticmethod
    def get_support_duration(obj):
        if obj.end:
            duration = obj.end - obj.start
        else:
            duration = date.today() - obj.start
        months = int(duration.days) // 30
        weeks = round(int(duration.days - months * 30) // 7, 0)
        return months + weeks / 10


class EngineerReportSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'project')

    @staticmethod
    def get_project(obj):
        projects = obj.projects.filter(
            statuses__is_current=True, project__start_date__lte=date.today(),
            statuses__frequency__in=['more_than_2_days', 'less_than_3_days'],
        ).exclude(project__statuses__status__istartswith='terminated', project__statuses__is_current=True)
        data = {
            "bandwidth": len(projects),
            "data": EngineerProjectSerializer(projects, many=True).data
        }
        return data


class EngineerTestSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'company_name', 'skills', 'consultant_name', 'client', 'job_title',
                  'marketer_name')

    @staticmethod
    def get_client(obj):
        return obj.submission.client

    @staticmethod
    def get_job_title(obj):
        return obj.submission.lead.job_title

    @staticmethod
    def get_company_name(obj):
        return obj.submission.lead.vendor_company.name

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_consultant_name(obj):
        return obj.submission.consultant_marketing.consultant.name


class EngineerInterviewSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = ('id', 'status', 'round', 'consultant_name', 'client',
                  'company_name', 'start_time', 'supervisor', 'marketer_name')

    @staticmethod
    def get_client(obj):
        return obj.submission.client

    @staticmethod
    def get_supervisor(obj):
        return obj.supervisor.employee_name

    @staticmethod
    def get_company_name(obj):
        return obj.submission.lead.vendor_company.name

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_consultant_name(obj):
        return obj.submission.consultant_marketing.consultant.name
