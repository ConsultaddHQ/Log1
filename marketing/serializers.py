from rest_framework import serializers

from marketing.models import *
from project.models import Project
from employee.serializers import UserSerializer
from activity.serializers import CommentGetSerializer
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
                  'owner', 'status', 'created', 'modified', 'is_w2')


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'created', 'duration', 'start_date', 'end_date', 'city', 'feedback', 'consultant',
                  'vendor_address', 'client_address', 'payment_term', 'invoicing_period', 'is_msg_sent', 'check_list',
                  'reporting_details', 'rate', 'employer', 'attachments', 'is_remote', 'consultant_name')

    def get_consultant_name(self, obj):
        return obj.consultant.name

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

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

        list_status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                               + reporting_details) / 6 >= 1 else False

        return {
            "total": 6,
            "msa": msa,
            "msa_signed": s_msa,
            "status": list_status,
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
    comments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    test = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'test', 'interviews', 'project', 'comments', 'marketer_name',
                  'marketer_id', 'consultant', 'is_complete')

    def get_marketer_name(self, obj):
        return obj.created_by.employee_name

    def get_marketer_id(self, obj):
        return obj.created_by.id

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_consultant(self, obj):
        return ConsultantSerializer(obj.consultant).data

    def get_comments(self, obj):
        return CommentGetSerializer(obj.comments.filter(parent_comment=None), many=True).data

    def get_interviews(self, obj):
        return InterviewGetSerializer(obj.screening.all().order_by('round'), many=True).data

    def get_test(self, obj):
        return TestCreateSerializer(obj.test.all().order_by('created'), many=True).data

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
    comments = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    test = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'test', 'project', 'comments', 'marketer_name',
                  'marketer_id', 'consultant', 'is_complete')

    def get_marketer_name(self, obj):
        return obj.created_by.employee_name

    def get_marketer_id(self, obj):
        return obj.created_by.id

    def get_consultant(self, obj):
        return ConsultantSerializer(obj.consultant).data

    def get_comments(self, obj):
        return CommentGetSerializer(obj.comments.filter(parent_comment=None), many=True).data

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

    def get_test(self, obj):
        return TestCreateSerializer(obj.test.all().order_by('created'), many=True).data


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
    attachment_link = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = '__all__'

    def get_attachment_link(self, obj):
        if obj.attachment_link:
            return obj.attachment_link.split('/')[-1]
        return None


class TestListSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    marketer_id = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'company_name', 'submission_id', 'marketer_name', 'marketer_id',
                  'consultant_name', 'client', 'job_title', 'skills', 'created', 'modified', 'assigned_to')

    def get_assigned_to(self, obj):
        return obj.assign_to.all().values('id', 'employee_name')

    def get_client(self, obj):
        return obj.submission.client

    def get_job_title(self, obj):
        return obj.submission.lead.job_title

    def get_company_name(self, obj):
        return obj.submission.lead.vendor_company.name

    def get_marketer_name(self, obj):
        return obj.submission.created_by.employee_name

    def get_consultant_name(self, obj):
        return obj.submission.consultant_marketing.consultant.name

    def get_marketer_id(self, obj):
        return obj.submission.created_by.id


class TestCreateSerializer(serializers.ModelSerializer):
    engineers = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'is_offline', 'feedback', 'link', 'additional_details', 'submit_date',
                  'engineer_remarks', 'is_video', 'skills', 'engineers', 'submitted_by', 'created', 'attachments',
                  'cancel_reason', 'assigned_to')

    def get_engineers(self, obj):
        if obj.engineer.all():
            return obj.engineer.all().values('id', 'employee_name')
        return None

    def get_assigned_to(self, obj):
        return obj.assign_to.all().values('id', 'employee_name')

    def get_submitted_by(self, obj):
        if obj.submitted_by:
            return {"id": obj.submitted_by.id, "employee_name": obj.submitted_by.employee_name}
        return None

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data


class TestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'
