from rest_framework import serializers

from consultant.models import *
from marketing.models import Submission, Interview
from attachment.serializers import AttachmentSerializer
from employee.serializers import UserSerializer
from employee.models import User
from project.models import ProjectSupport


class ConsultantPOCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email')


class WorkAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkAuth
        exclude = ('created', 'modified', 'consultant')


class ConsultantProfileSerializer(serializers.ModelSerializer):
    profile_owner = ConsultantPOCSerializer()

    class Meta:
        model = ConsultantProfile
        fields = ('title', 'visa_type', 'visa_start', 'visa_end', 'education', 'date_of_birth', 'links', 'linkedin',
                  'current_city', 'profile_owner')


class ConsultantSerializer(serializers.ModelSerializer):
    work_auth = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    relation = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()

    @staticmethod
    def get_work_auth(self):
        return WorkAuthSerializer(self.work_auth.filter(is_current=True), many=True).data

    @staticmethod
    def get_profiles(self):
        return ConsultantProfileSerializer(self.profiles.all(), many=True).data

    @staticmethod
    def get_recruiter(self):
        queryset = self.pocs.filter(end=None, poc_type='recruiter')
        if queryset:
            poc = queryset.first().poc
            return ConsultantPOCSerializer(poc).data
        return None

    @staticmethod
    def get_relation(self):
        queryset = self.pocs.filter(end=None, poc_type='relation')
        if queryset:
            poc = queryset.first().poc
            return ConsultantPOCSerializer(poc).data
        return None

    @staticmethod
    def get_support(self):
        queryset = ProjectSupport.objects.filter(project__consultant=self, end=None)
        if queryset:
            poc = queryset.first().engineer
            return ConsultantPOCSerializer(poc).data
        return None

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'ssn', 'gender', 'phone_no', 'links', 'skills', 'skype', 'status',
                  'date_of_birth', 'work_type', 'current_city', 'work_auth', 'recruiter', 'relation', 'support', 'profiles')
