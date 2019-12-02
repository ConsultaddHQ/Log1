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
    marketer = serializers.SerializerMethodField()

    @staticmethod
    def get_vendor_company_name(self):
        return self.vendor_company.name if self.vendor_company else None

    @staticmethod
    def get_marketer(self):
        return self.marketer.employee_name

    class Meta:
        model = Lead
        fields = ('id', 'job_desc', 'job_title', 'primary_skill', 'city', 'vendor_company_id', 'vendor_company_name',
                  'marketer', 'status', 'created', 'modified')


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
    project = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'attachments', 'interviews', 'project')

    @staticmethod
    def get_attachments(self):
        return AttachmentSerializer(self.attachments.all(), many=True).data

    @staticmethod
    def get_interviews(self):
        return InterviewGetSerializer(self.screening.all(), many=True).data

    @staticmethod
    def get_project(self):
        if hasattr(self, 'project'):
            return ProjectSerializer(self.project).data
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    vendor_contact = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'attachments', 'interviews', 'project')

    @staticmethod
    def get_attachments(self):
        return []

    @staticmethod
    def get_vendor_contact(self):
        return None

    @staticmethod
    def get_interviews(self):
        return InterviewGetSerializer(self.screening.all(), many=True).data

    @staticmethod
    def get_project(self):
        if hasattr(self, 'project'):
            return ProjectSerializer(self.project).data
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
