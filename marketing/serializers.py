from rest_framework import serializers

from marketing.models import *
from project.models import Project
from employee.serializers import UserSerializer
from attachment.serializers import AttachmentSerializer


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

    @staticmethod
    def get_vendor_company_name(self):
        return self.vendor_company.name if self.vendor_company else None

    @staticmethod
    def get_owner(self):
        return self.owner.employee_name

    class Meta:
        model = Lead
        fields = ('id', 'job_desc', 'job_title', 'primary_skill', 'city', 'vendor_company_id', 'vendor_company_name',
                  'owner', 'status', 'created', 'modified')


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class SubmissionDetailSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'project', 'created_by')

    def get_created_by(self, obj):
        return obj.created_by.employee_name

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_interviews(self, obj):
        return InterviewGetSerializer(obj.screening.all(), many=True).data

    def get_project(self, obj):
        if hasattr(self, 'project'):
            return ProjectSerializer(obj.project).data
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    vendor_contact = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'project', 'created_by')

    def get_created_by(self, obj):
        return obj.created_by.employee_name

    def get_attachments(self):
        return []

    def get_vendor_contact(self):
        return None

    def get_interviews(self, obj):
        return InterviewGetSerializer(obj.screening.all(), many=True).data

    def get_project(self, obj):
        if hasattr(self, 'project'):
            return ProjectSerializer(obj.project).data
        return None


class VendorLayerSerializer(serializers.ModelSerializer):
    company = VendorCompanySerializer()

    class Meta:
        model = VendorLayer
        fields = '__all__'


class InterviewSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    guest = UserSerializer(many=True)
    ctb = UserSerializer()

    class Meta:
        model = Interview
        fields = '__all__'


class InterviewDetailSerializer(serializers.ModelSerializer):
    submission = SubmissionDetailSerializer()
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
