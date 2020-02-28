from rest_framework import serializers

from project.models import *
from marketing.serializers import InterviewGetSerializer, SubmissionSerializer
from attachment.serializers import AttachmentSerializer


class ProjectSerializer(serializers.ModelSerializer):
    rate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'feedback', 'created', 'duration', 'submission', 'start_date', 'client', 'rate',
                  'end_date', 'consultant_name', 'city', 'check_list', 'marketer_name', 'company_name')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_rate(self, obj):
        return obj.submission.rate

    def get_marketer_name(self, obj):
        return obj.submission.created_by.employee_name

    def get_client(self, obj):
        return obj.submission.client

    def get_consultant_name(self, obj):
        return obj.submission.consultant.name

    def get_company_name(self, obj):
        return obj.submission.lead.vendor_company.name

    def get_check_list(self, obj):
        msa, client_address, vendor_address, work_order, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0, 0, 0

        start_date = 1 if obj.start_date else 0

        if obj.attachments.filter(attachment_type='msa'):
            msa = 1

        if obj.attachments.filter(attachment_type='work_order'):
            work_order = 1

        if obj.attachments.filter(attachment_type='work_order_msa'):
            msa, work_order = 1, 1

        if obj.attachments.filter(attachment_type='msa_signed'):
            s_msa = 1

        if obj.attachments.filter(attachment_type='work_order_signed'):
            s_work_order = 1

        if obj.attachments.filter(attachment_type='work_order_msa_signed'):
            s_msa, s_work_order = 1, 1

        if obj.client_address and len(obj.client_address.strip()) > 0:
            client_address = 1

        if obj.vendor_address and len(obj.vendor_address.strip()) > 0:
            vendor_address = 1

        if obj.reporting_details and len(obj.reporting_details.strip()) > 0:
            reporting_details = 1

        status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                          + reporting_details) / 6 >= 1 else False

        return {
            "total": 6,
            "msa": msa,
            "status": status,
            "msa_signed": s_msa,
            "work_order": work_order,
            "start_date": start_date,
            "client_address": client_address,
            "vendor_address": vendor_address,
            "work_order_signed": s_work_order,
            "reporting_details": reporting_details,
        }


class PayrollScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollSchedule
        fields = '__all__'


class TimeSheetSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'status_updated_at', 'status_updated_by',
                  'modified', 'attachments', 'project')

    def get_attachments(self, obj: Attachment) -> dict:
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_project(self, obj):
        return {
            'id': obj.project.id,
            'start_date': obj.project.start_date,
            'client': obj.project.submission.client
        }


class ConsultantTimeSheetSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    ts_status = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'ts_status', 'project')

    def get_project(self, obj):
        project = Project.objects.filter(consultant=obj)
        if project:
            project = project.latest('id')
            return {
                'id': project.id,
                'start_date': project.start_date,
                'team': project.submission.employer,
                'client': project.submission.client,
                'vendor': project.submission.lead.vendor_company.name,
            }
        return None

    def get_ts_status(self, obj):
        queryset = TimeSheet.objects.filter(project__consultant=obj)
        sub_ts = True if queryset.filter(status='submitted') else False
        rej_ts = True if queryset.filter(status='rejected', is_active=True) else False
        data = {
            'rejected': rej_ts,
            'submitted': sub_ts,
        }
        return data


class ProjectGetSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    status = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'submission', 'feedback', 'check_list', 'attachments', 'created',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'reporting_details')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_check_list(self, obj):
        msa, client_address, vendor_address, work_order, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0, 0, 0

        start_date = 1 if obj.start_date else 0

        if obj.attachments.filter(attachment_type='msa'):
            msa = 1

        if obj.attachments.filter(attachment_type='work_order'):
            work_order = 1

        if obj.attachments.filter(attachment_type='work_order_msa'):
            msa, work_order = 1, 1

        if obj.attachments.filter(attachment_type='msa_signed'):
            s_msa = 1

        if obj.attachments.filter(attachment_type='work_order_signed'):
            s_work_order = 1

        if obj.attachments.filter(attachment_type='work_order_msa_signed'):
            s_msa, s_work_order = 1, 1

        if obj.client_address and len(obj.client_address.strip()) > 0:
            client_address = 1

        if obj.vendor_address and len(obj.vendor_address.strip()) > 0:
            vendor_address = 1

        if obj.reporting_details and len(obj.reporting_details.strip()) > 0:
            reporting_details = 1

        status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                          + reporting_details) / 6 >= 1 else False

        return {
            "total": 6,
            "msa": msa,
            "status": status,
            "msa_signed": s_msa,
            "work_order": work_order,
            "start_date": start_date,
            "client_address": client_address,
            "vendor_address": vendor_address,
            "work_order_signed": s_work_order,
            "reporting_details": reporting_details,
        }
