from rest_framework import serializers

from marketing.models import *
from project.models import Project
from employee.serializers import UserSerializer
from attachment.serializers import AttachmentSerializer
from consultant.serializers import ConsultantSerializer


class VendorCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCompany
        fields = '__all__'


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = '__all__'


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    vendor_company_name = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    def get_vendor_company_name(self, obj):
        return obj.vendor_company.name if obj.vendor_company else None

    def get_owner(self, obj):
        return obj.owner.employee_name

    class Meta:
        model = Lead
        fields = ('id', 'job_desc', 'job_title', 'primary_skill', 'city', 'vendor_company_id', 'vendor_company_name',
                  'owner', 'status', 'created', 'modified')


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    check_list = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'created', 'duration', 'start_date', 'end_date', 'city', 'feedback', 'consultant',
                  'vendor_address', 'client_address', 'payment_term', 'invoicing_period', 'is_msg_sent', 'check_list')

    def get_status(self, obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

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

        return {
            "total": 6,
            "msa": msa,
            "msa_signed": s_msa,
            "work_order": work_order,
            "start_date": start_date,
            "client_address": client_address,
            "vendor_address": vendor_address,
            "work_order_signed": s_work_order,
            "reporting_details": reporting_details,
        }


class SubmissionDetailSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    marketer_id = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'project', 'marketer_name', 'marketer_id', 'consultant')

    def get_marketer_name(self, obj):
        return obj.created_by.employee_name

    def get_marketer_id(self, obj):
        return obj.created_by.id

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_consultant(self, obj):
        return ConsultantSerializer(obj.consultant).data

    def get_interviews(self, obj):
        return InterviewGetSerializer(obj.screening.all().order_by('round'), many=True).data

    def get_project(self, obj):
        if hasattr(obj, 'project'):
            return ProjectSerializer(obj.project).data
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    vendor_contact = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    marketer_id = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'project', 'marketer_name', 'marketer_id', 'consultant')

    def get_marketer_name(self, obj):
        return obj.created_by.employee_name

    def get_marketer_id(self, obj):
        return obj.created_by.id

    def get_consultant(self, obj):
        return ConsultantSerializer(obj.consultant).data

    def get_attachments(self, obj):
        return []

    def get_vendor_contact(self, obj):
        return None

    def get_project(self, obj):
        if hasattr(obj, 'project'):
            return ProjectSerializer(obj.project).data
        return None

    def get_interviews(self, obj):
        return InterviewGetSerializer(obj.screening.all().order_by('round'), many=True).data


class VendorLayerSerializer(serializers.ModelSerializer):
    vendor_company = VendorCompanySerializer()

    class Meta:
        model = VendorLayer
        fields = '__all__'


class InterviewSerializer(serializers.ModelSerializer):
    submission = SubmissionCreateSerializer()
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        fields = '__all__'


class InterviewDetailSerializer(serializers.ModelSerializer):
    submission = SubmissionCreateSerializer()
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        fields = '__all__'


class InterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = '__all__'


class InterviewGetSerializer(serializers.ModelSerializer):
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        fields = '__all__'
