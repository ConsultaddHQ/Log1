from django.db.models import F
from rest_framework import serializers

from consultant.models import *
from employee.models import User
from marketing.models import Interview
from project.models import Project, ProjectSupport
from employee.serializers import TeamSerializer, UserSerializer


# Consultant Login
class ConsultantLoginSerializer(UserSerializer):
    token = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'token', 'email', 'name', 'is_active', 'project', 'first_login')

    def get_project(self, obj):
        if hasattr(obj, 'projects'):
            return obj.projects.filter(end_date=None).annotate(
                client=F('submission__client'),
                employer=F('submission__employer')
            ).values('id', 'start_date', 'client', 'employer')
        return False

    def get_token(self, obj):
        token, created = ConsultantToken.objects.get_or_create(consultant=obj)
        return token.key


class ConsultantPetitionLoginSerializer(UserSerializer):
    token = serializers.SerializerMethodField()
    petition = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'token', 'email', 'name', 'petition')

    def get_petition(self, obj):
        petitions = obj.petitions.filter(is_active=True)
        if petitions:
            petition = petitions.first()
            return {
                "id": petition.id,
                "status": petition.status,
                "assigned_to": UserSerializer(petition.assigned_to).data
            }
        return None

    def get_token(self, obj):
        token, created = ConsultantPetitionToken.objects.get_or_create(consultant=obj)
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

    def get_marketer(self, obj):
        return obj.marketer.all().annotate(name=F('employee_name')).values('id', 'name')

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'teams', 'marketer', 'status', 'in_pool', 'rtg', 'start', 'end', 'preferred_location',
                  'primary_marketer')


class ConsultantMarketingCycleSerializer(serializers.ModelSerializer):
    primary_marketer_team = serializers.SerializerMethodField()
    primary_marketer = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    current_city = serializers.SerializerMethodField()
    teams = TeamSerializer(many=True)

    def get_primary_marketer(self, obj):
        return obj.primary_marketer.employee_name if obj.primary_marketer else None

    def get_primary_marketer_team(self, obj):
        return obj.primary_marketer.team.name if obj.primary_marketer else None

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def get_current_city(self, obj):
        return obj.consultant.current_city

    def get_project_count(self, obj):
        return Project.objects.filter(submission__consultant_marketing=obj).count()

    def get_interview_count(self, obj):
        return Interview.objects.filter(
            submission__consultant_marketing=obj
        ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'cycle', 'teams', 'status', 'in_pool', 'rtg', 'start', 'end', 'preferred_location',
                  'primary_marketer', 'primary_marketer_team', 'submission_count', 'interview_count',
                  'project_count', 'current_city')


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
    rate = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    relation = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    work_auth = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'ssn', 'gender', 'phone_no', 'links', 'skills', 'skype', 'status',
                  'date_of_birth', 'work_type', 'current_city', 'work_auth', 'recruiter', 'relation', 'support',
                  'profiles', 'education', 'experience', 'rate', 'marketing')

    def get_work_auth(self, obj):
        return WorkAuthSerializer(obj.work_auth.all(), many=True).data

    def get_profiles(self, obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    def get_education(self, obj):
        return EducationSerializer(obj.academics.all(), many=True).data

    def get_experience(self, obj):
        return ExperienceSerializer(obj.experiences.all(), many=True).data

    def get_rate(self, obj):
        rate_revision = obj.rates.filter(end=None)
        if rate_revision:
            return rate_revision.first().rate
        return 0

    def get_marketing(self, obj):
        marketing = obj.marketing.filter(status='open')
        if marketing:
            return ConsultantMarketingSerializer(marketing, many=True).data[0]
        else:
            return None

    def get_recruiter(self, obj):
        queryset = obj.pocs.filter(end=None, poc_type='recruiter')
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

    def get_relation(self, obj):
        queryset = obj.pocs.filter(end=None, poc_type='relation')
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

    def get_support(self, obj):
        queryset = ProjectSupport.objects.filter(project__consultant=obj, end=None)
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

    def get_profiles(self, obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'profiles')
