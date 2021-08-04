from rest_framework import serializers

from consultant.models import Consultant
from project.utils import get_project_check_list
from project.models import Project, ProjectSupport
from activity.serializers import CommentGetSerializer
from consultant.serializers import ConsultantSerializer
from employee.serializers import UserSerializer, UserDetailSerializer
from attachment.serializers import AttachmentSerializer, AttachmentGetSerializer
from marketing.models import Lead, Test, Submission, Interview, VendorCompany, VendorLayer, VendorContact


class VendorCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCompany
        fields = '__all__'


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = ('id', 'name', 'email', 'number')


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()
    vendor_company_name = serializers.SerializerMethodField()

    @staticmethod
    def get_vendor_company_name(obj):
        return obj.vendor_company.name if obj.vendor_company else None

    @staticmethod
    def get_owner(obj):
        return obj.owner.employee_name

    @staticmethod
    def get_position_name(obj):
        if obj.position:
            return obj.position.display_name
        return None

    class Meta:
        model = Lead
        fields = ('id', 'job_desc', 'job_title', 'primary_skill', 'city', 'vendor_company_id', 'vendor_company_name',
                  'owner', 'status', 'created', 'modified', 'is_w2', 'position_name')


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

    @staticmethod
    def get_consultant_name(obj):
        return obj.consultant.name

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)


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

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_marketer_id(obj):
        return obj.created_by.id

    @staticmethod
    def get_consultant(obj):
        return ConsultantSerializer(obj.consultant).data

    @staticmethod
    def get_comments(obj):
        return CommentGetSerializer(obj.comments.filter(parent_comment=None), many=True).data

    @staticmethod
    def get_attachments(self):
        return []

    @staticmethod
    def get_vendor_contact(obj):
        return None

    @staticmethod
    def get_project(obj):
        if hasattr(obj, 'project'):
            return ProjectSerializer(obj.project).data
        return None

    @staticmethod
    def get_interviews(obj):
        return InterviewGetSerializer(obj.screening.all().order_by('round'), many=True).data

    @staticmethod
    def get_test(obj):
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
        exclude = ('calendar_id',)


class InterviewDetailSerializer(serializers.ModelSerializer):
    submission = SubmissionCreateSerializer()
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)


class InterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        exclude = ('calendar_id',)


class InterviewGetSerializer(serializers.ModelSerializer):
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()
    attachment_link = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)

    @staticmethod
    def get_attachment_link(obj):
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

    @staticmethod
    def get_client(obj):
        return obj.submission.client

    @staticmethod
    def get_marketer_id(obj):
        return obj.submission.created_by.id

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
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_consultant_name(obj):
        return obj.submission.consultant_marketing.consultant.name


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

    @staticmethod
    def get_engineers(obj):
        if obj.engineer.all():
            return obj.engineer.all().values('id', 'employee_name')
        return None

    @staticmethod
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_submitted_by(obj):
        if obj.submitted_by:
            return {"id": obj.submitted_by.id, "employee_name": obj.submitted_by.employee_name}
        return None

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data


class TestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'


class SubmissionV2Serializer(serializers.ModelSerializer):
    vendor_contact = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    vendor_layer = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'marketer_name', 'is_complete', 'vendor_layer')

    @staticmethod
    def get_vendor_layer(obj):
        return []

    @staticmethod
    def get_vendor_contact(obj):
        return None

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name


class SubmissionV2DetailSerializer(serializers.ModelSerializer):
    vendor_layer = VendorLayerSerializer(read_only=True)
    marketer_name = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'marketer_name', 'is_complete', 'vendor_layer')

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name


class SubmissionConProfile(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'current_city', 'phone_no', 'status', 'profile')

    def get_profile(self, obj):
        submission = self.context['submission']
        return {
            "linkedin": submission.linkedin,
            "visa_end": submission.visa_end,
            "education": submission.education,
            "visa_type": submission.visa_type,
            "other_link": submission.other_link,
            "visa_start": submission.visa_start,
            "current_city": submission.current_city,
            "date_of_birth": submission.date_of_birth,
        }


class InterviewV2Serializer(serializers.ModelSerializer):
    supervisor = UserDetailSerializer()
    guest = UserDetailSerializer(many=True)
    permission = serializers.SerializerMethodField()
    attachment_link = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)

    def get_permission(self, obj):
        user = self.context.get('user')
        update = False
        if user in [obj.marketer, obj.supervisor]:
            update = True
        return {'update': update}

    @staticmethod
    def get_attachment_link(obj):
        if obj.attachment_link:
            return obj.attachment_link.split('/')[-1]
        return None


class TestGetSerializer(serializers.ModelSerializer):
    engineers = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    attachments = AttachmentGetSerializer(many=True)
    assigned_to = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'is_offline', 'feedback', 'link', 'additional_details', 'submit_date',
                  'engineer_remarks', 'is_video', 'skills', 'engineers', 'submitted_by', 'created', 'attachments',
                  'cancel_reason', 'assigned_to', 'permission')

    @staticmethod
    def get_engineers(obj):
        if obj.engineer.all():
            return obj.engineer.all().values('id', 'employee_name')
        return None

    @staticmethod
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_submitted_by(obj):
        if obj.submitted_by:
            return {
                "id": obj.submitted_by.id,
                "employee_name": obj.submitted_by.employee_name,
            }
        return None

    def get_permission(self, obj):
        user = self.context.get('user')
        update = False
        if user == obj.marketer:
            update = True
        return {'update': update}


class SubmissionSupportSerializer(serializers.ModelSerializer):
    support = UserDetailSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = '__all__'

    @staticmethod
    def get_status(obj):
        statuses = obj.statuses.filter(is_current=True)
        if statuses:
            support_status = statuses.first()
            return {"id": support_status.id, "frequency": support_status.frequency}
        return None


class ProjectV2Serializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    remote_consultant = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'feedback', 'check_list', 'attachments', 'created', 'city', 'remote_consultant',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'rate', 'employer', 'reporting_details', 'is_remote', 'permission')

    @staticmethod
    def get_remote_consultant(obj):
        return {
            "id": obj.consultant.id,
            "name": obj.consultant.name
        }

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_permission(self, obj):
        user = self.context.get('user')
        update = False
        if user == obj.submission.created_by or 'finance' in user.roles:
            update = True
        return {'update': update}

    @staticmethod
    def get_attachments(obj):
        return AttachmentGetSerializer(obj.attachments.all(), many=True).data

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)
