from django.db.models import F
from rest_framework import serializers

from consultant.models import *
from employee.models import User
from project.models import ProjectSupport
from employee.serializers import TeamSerializer


class ConsultantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultant
        fields = '__all__'


class ConsultantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultant
        exclude = ('created', 'modified')


class POCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'employee_name', 'email', 'phone')


class ConsultantMarketingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantMarketing
        exclude = ('id', 'cycle', 'teams', 'marketer', 'created', 'modified')


class ConsultantMarketingSerializer(serializers.ModelSerializer):
    primary_marketer = POCSerializer()
    teams = TeamSerializer(many=True)
    marketer = serializers.SerializerMethodField()

    @staticmethod
    def get_marketer(self):
        return self.marketer.all().annotate(name=F('employee_name')).values('id', 'name')

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'teams', 'marketer', 'in_pool', 'rtg', 'start', 'end', 'preferred_location', 'primary_marketer')


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
    feedback = FeedbackDetailsSerializer(many=True)

    class Meta:
        model = ConsultantFeedback
        fields = '__all__'


class ConsultantProfileSerializer(serializers.ModelSerializer):
    profile_owner = POCSerializer()

    class Meta:
        model = ConsultantProfile
        fields = ('id', 'title', 'visa_type', 'visa_start', 'visa_end', 'education', 'date_of_birth', 'links',
                  'linkedin', 'current_city', 'profile_owner')


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
        return ConsultantMarketingSerializer(self.marketing.filter(end=None), many=True).data[0]

    @staticmethod
    def get_recruiter(self):
        queryset = self.pocs.filter(end=None, poc_type='recruiter')
        if queryset:
            poc = queryset.first().poc
            return POCSerializer(poc).data
        return None

    @staticmethod
    def get_relation(self):
        queryset = self.pocs.filter(end=None, poc_type='relation')
        if queryset:
            poc = queryset.first().poc
            return POCSerializer(poc).data
        return None

    @staticmethod
    def get_support(self):
        queryset = ProjectSupport.objects.filter(project__consultant=self, end=None)
        if queryset:
            poc = queryset.first().engineer
            return POCSerializer(poc).data
        return None

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'ssn', 'gender', 'phone_no', 'links', 'skills', 'skype', 'status',
                  'date_of_birth', 'work_type', 'current_city', 'work_auth', 'recruiter', 'relation', 'support',
                  'profiles', 'education', 'experience', 'rate', 'marketing')


class ConsultantListSerializer(serializers.ModelSerializer):
    profiles = serializers.SerializerMethodField()

    @staticmethod
    def get_profiles(self):
        return ConsultantProfileSerializer(self.profiles.all(), many=True).data

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'profiles')
