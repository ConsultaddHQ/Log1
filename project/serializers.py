from datetime import date
from django.db.models import Q
from rest_framework import serializers

from consultant.models import Consultant
from employee.serializers import UserSerializer
from utils_app.utils import get_project_check_list
from marketing.serializers import SubmissionSerializer
from attachment.serializers import AttachmentSerializer, AttachmentURLSerializer
from project.models import Project, ProjectOrder, ProjectSupport, SupportStatus, TimeSheet, PayrollSchedule


class ProjectSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'feedback', 'created', 'duration', 'submission', 'start_date', 'client', 'rate',
                  'city', 'end_date', 'consultant_name', 'city', 'check_list', 'marketer_name', 'company_name',
                  'is_remote', 'support', 'employer')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_support(self, obj):
        return ProjectSupportSerializer(obj.support.all(), many=True).data

    def get_marketer_name(self, obj):
        return obj.submission.created_by.employee_name

    def get_client(self, obj):
        return obj.submission.client

    def get_consultant_name(self, obj):
        if obj.consultant:
            if obj.is_remote:
                firstname = obj.consultant.name.split(' ')[0]
                return f"{obj.submission.consultant.name} ({firstname})"
            else:
                return obj.consultant.name
        return None

    def get_company_name(self, obj):
        return obj.submission.lead.vendor_company.name

    def get_check_list(self, obj):
        return get_project_check_list(obj)


class PayrollScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollSchedule
        fields = '__all__'


class TimeSheetSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'attachments', 'remark', 'project', 'con_comment')

    def get_start(self, obj):
        return obj.start.strftime("%m/%d/%Y")

    def get_end(self, obj):
        return obj.end.strftime("%m/%d/%Y")

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_project(self, obj):
        return {
            'id': obj.project.id,
            'employer': obj.project.employer,
            'start_date': obj.project.start_date,
            'client': obj.project.submission.client,
            'vendor': obj.project.submission.lead.vendor_company.name,
        }


class FinanceSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'attachments', 'remark', 'project', 'con_comment')

    def get_start(self, obj):
        return obj.start.strftime("%m/%d/%Y")

    def get_end(self, obj):
        return obj.end.strftime("%m/%d/%Y")

    def get_attachments(self, obj):
        return AttachmentURLSerializer(obj.attachments.all(), many=True).data

    def get_project(self, obj):
        return {
            'id': obj.project.id,
            'employer': obj.project.employer,
            'start_date': obj.project.start_date,
            'client': obj.project.submission.client,
            'vendor': obj.project.submission.lead.vendor_company.name,
        }


class ConsultantTimeSheetSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    ts_status = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'ts_status', 'project')

    def get_project(self, obj):
        project = Project.objects.filter(
            Q(consultant=obj, statuses__is_current=True) & (
                    Q(statuses__status__istartswith='terminated') |
                    Q(statuses__status__in=['joined', 'complete', 'extended'])
            )
        )
        if project:
            project = project.latest('-start_date')
            return {
                'id': project.id,
                'team': project.employer,
                'start_date': project.start_date,
                'client': project.submission.client,
                'vendor': project.submission.lead.vendor_company.name,
            }
        return None

    def get_ts_status(self, obj):
        queryset = TimeSheet.objects.filter(project__consultant=obj)
        submitted_ts = True if queryset.filter(status='submitted') else False
        rejected_ts = True if queryset.filter(status='rejected', is_active=True) else False
        return {'submitted': submitted_ts, 'rejected': rejected_ts}


class ProjectGetSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    status = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'submission', 'feedback', 'check_list', 'attachments', 'created', 'city',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'rate', 'employer', 'reporting_details', 'is_remote', 'marketer_name')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_marketer_name(self, obj):
        return obj.submission.created_by.employee_name

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_check_list(self, obj):
        return get_project_check_list(obj)


class SupportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportStatus
        fields = '__all__'


class ProjectSupportSerializer(serializers.ModelSerializer):
    support = UserSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = '__all__'

    def get_status(self, obj):
        return SupportStatusSerializer(obj.statuses.filter(is_current=True).first()).data


class ProjectSupportDetailSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    technology = serializers.SerializerMethodField()
    frequency = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    joining_date = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = ('id', 'created', 'is_primary', 'end', 'start', 'feedback', 'status',
                  'client', 'consultant', 'technology', 'support', 'joining_date', 'frequency')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True).first()
        if obj.project.statuses.filter(status__istartswith='terminated').first():
            return 'terminated'
        elif obj.project.start_date and obj.project.start_date > date.today():
            return 'training'
        elif status:
            if status.frequency == 'more_than_2_days':
                return 'active'
            elif status.frequency == 'less_than_3_days':
                return 'less_active'
            elif status.frequency in ('twice_a_month', 'independent'):
                return 'independent'
        else:
            return None

    def get_frequency(self, obj):
        status = obj.statuses.filter(is_current=True).first()
        if status:
            return status.frequency
        return None

    def get_client(self, obj):
        return obj.project.submission.client

    def get_support(self, obj):
        return UserSerializer(obj.support).data

    def get_technology(self, obj):
        return obj.project.submission.lead.primary_skill

    def get_joining_date(self, obj):
        return obj.project.start_date

    def get_consultant(self, obj):
        data = {
            'name': obj.project.consultant.name,
            'email': obj.project.consultant.email,
            'contact': obj.project.consultant.phone_no
        }
        return data


class ProjectOrderSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ProjectOrder
        fields = '__all__'

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.project.attachments.all(), many=True).data
