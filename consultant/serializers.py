from django.db.models import F
from rest_framework import serializers

from consultant.models import *
from employee.models import User
from project.models import ProjectSupport
from employee.serializers import TeamSerializer, UserSerializer


# Consultant Login
class ConsultantLoginSerializer(UserSerializer):
    token = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'token', 'email', 'name', 'is_active', 'project', 'first_login')

    @staticmethod
    def get_project(self):
        if hasattr(self, 'projects'):
            return self.projects.filter(end_date=None).annotate(
                client=F('submission__client'),
                employer=F('submission__employer')
            ).values('id', 'start_date', 'client', 'employer')
        return False

    @staticmethod
    def get_token(self):
        token, created = ConsultantToken.objects.get_or_create(consultant=self)
        return token.key


class ConsultantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultant
        exclude = ('password',)


class ConsultantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultant
        exclude = ('password', 'created', 'modified')


class POCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email', 'phone')


class ConsultantMarketingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantMarketing
        exclude = ('teams', 'marketer', 'created', 'modified')


class ConsultantMarketingSerializer(serializers.ModelSerializer):
    primary_marketer = POCSerializer()
    teams = TeamSerializer(many=True)
    marketer = serializers.SerializerMethodField()

    @staticmethod
    def get_marketer(self):
        return self.marketer.all().annotate(name=F('employee_name')).values('id', 'name')

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'teams', 'marketer', 'status', 'in_pool', 'rtg', 'start', 'end', 'preferred_location',
                  'primary_marketer')


class ConsultantRateRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantRateRevision
        fields = '__all__'


class ConsultantPOCSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantPOC
        exclude = ('created', 'modified')


class WorkAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkAuth
        exclude = ('created', 'modified')


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = '__all__'


class FeedbackDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackDetail
        fields = '__all__'


class ConsultantFeedbackSerializer(serializers.ModelSerializer):
    feedback = FeedbackDetailsSerializer()
    given_by = POCSerializer()
    created_by = POCSerializer()

    class Meta:
        model = ConsultantFeedback
        fields = '__all__'


class ConsultantProfileSerializer(serializers.ModelSerializer):
    profile_owner = POCSerializer()

    class Meta:
        model = ConsultantProfile
        fields = ('id', 'title', 'visa_type', 'visa_start', 'visa_end', 'education', 'date_of_birth', 'links',
                  'linkedin', 'current_city', 'profile_owner')


class ConsultantCreateProfileSerializer(serializers.ModelSerializer):
    profile_owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ConsultantProfile
        fields = ('id', 'title', 'visa_type', 'visa_start', 'visa_end', 'education', 'date_of_birth', 'links',
                  'linkedin', 'current_city', 'profile_owner')


class ConsultantSubmissionSerializer(serializers.ModelSerializer):
    profiles = serializers.SerializerMethodField()
    marketing_id = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'status', 'profiles', 'marketing_id')

    def get_profiles(self, obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    def get_marketing_id(self, obj):
        queryset = obj.marketing.filter(status='open')
        if queryset:
            return queryset.first().id
        return None


class ConsultantBenchSerializer(serializers.ModelSerializer):
    support = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    relation = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    work_auth = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'ssn', 'gender', 'phone_no', 'links', 'skills', 'skype', 'status',
                  'date_of_birth', 'work_type', 'current_city', 'work_auth', 'recruiter', 'relation', 'support',
                  'profiles', 'education', 'experience', 'rate', 'marketing')

    @staticmethod
    def get_work_auth(self):
        return WorkAuthSerializer(self.work_auth.filter(is_current=True), many=True).data

    @staticmethod
    def get_profiles(self):
        return ConsultantProfileSerializer(self.profiles.all(), many=True).data

    @staticmethod
    def get_education(self):
        return EducationSerializer(self.academics.all(), many=True).data

    @staticmethod
    def get_experience(self):
        return EducationSerializer(self.experiences.all(), many=True).data

    @staticmethod
    def get_rate(self):
        rate_revision = self.rates.filter(end=None)
        if rate_revision:
            return rate_revision.first().rate
        return 0

    @staticmethod
    def get_marketing(self):
        marketing = self.marketing.filter(status='open')
        if marketing:
            return ConsultantMarketingSerializer(marketing, many=True).data[0]
        else:
            return None

    @staticmethod
    def get_recruiter(self):
        queryset = self.pocs.filter(end=None, poc_type='recruiter')
        if queryset:
            poc = queryset.first().poc
            data = {
                "id": queryset.first().id,
                'user_id': poc.id,
                'email': poc.email,
                'phone': poc.phone,
                'employee_name': poc.employee_name,
            }
            return data
        return None

    @staticmethod
    def get_relation(self):
        queryset = self.pocs.filter(end=None, poc_type='relation')
        if queryset:
            poc = queryset.first().poc
            data = {
                "id": queryset.first().id,
                'user_id': poc.id,
                'email': poc.email,
                'phone': poc.phone,
                'employee_name': poc.employee_name,
            }
            return data
        return None

    @staticmethod
    def get_support(self):
        queryset = ProjectSupport.objects.filter(project__consultant=self, end=None)
        if queryset:
            poc = queryset.first().engineer
            data = {
                "id": queryset.first().id,
                'user_id': poc.id,
                'email': poc.email,
                'phone': poc.phone,
                'employee_name': poc.employee_name,
            }
            return data
        return None


class ConsultantListSerializer(serializers.ModelSerializer):
    profiles = serializers.SerializerMethodField()

    @staticmethod
    def get_profiles(self):
        return ConsultantProfileSerializer(self.profiles.all(), many=True).data

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'profiles')
