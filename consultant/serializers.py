from django.db.models import F, Q
from datetime import date, timedelta
from rest_framework import serializers

from consultant.models import *
from project.models import Project
from marketing.models import Interview
from project.models import ConsultantFeedback
from employee.serializers import TeamSerializer, UserSerializer, TaggedUserSerializer


# Consultant Login
class ConsultantLoginSerializer(UserSerializer):
    token = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'token', 'email', 'name', 'is_active', 'project', 'first_login')

    @staticmethod
    def get_project(obj):
        if hasattr(obj, 'projects'):
            return obj.projects.filter(end_date=None).annotate(
                client=F('submission__client'),
                employer=F('submission__employer')
            ).values('id', 'start_date', 'client', 'employer')
        return False

    @staticmethod
    def get_token(obj):
        token, created = ConsultantToken.objects.get_or_create(consultant=obj)
        return token.key


class ConsultantPetitionLoginSerializer(UserSerializer):
    token = serializers.SerializerMethodField()
    petition = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'token', 'email', 'name', 'petition')

    @staticmethod
    def get_petition(obj):
        petitions = obj.petitions.filter(is_active=True)
        if petitions:
            petition = petitions.first()
            return {
                "id": petition.id,
                "status": petition.status,
                "petition_type": petition.petition_type,
                "assigned_to": UserSerializer(petition.assigned_to).data,
            }
        return None

    @staticmethod
    def get_token(obj):
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

    @staticmethod
    def get_marketer(obj):
        return obj.marketer.all().annotate(name=F('employee_name')).values('id', 'name')

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'teams', 'marketer', 'status', 'in_pool', 'rtg', 'start', 'end', 'preferred_location',
                  'primary_marketer', 'previous_marketing_days')


class ConsultantMarketingCycleSerializer(serializers.ModelSerializer):
    primary_marketer_team = serializers.SerializerMethodField()
    primary_marketer = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    current_city = serializers.SerializerMethodField()
    teams = TeamSerializer(many=True)

    class Meta:
        model = ConsultantMarketing
        fields = ('id', 'cycle', 'teams', 'status', 'in_pool', 'rtg', 'start', 'end', 'preferred_location',
                  'project_count', 'primary_marketer', 'primary_marketer_team', 'submission_count', 'interview_count',
                  'current_city')

    @staticmethod
    def get_primary_marketer(obj):
        return obj.primary_marketer.employee_name if obj.primary_marketer else None

    @staticmethod
    def get_primary_marketer_team(obj):
        return obj.primary_marketer.team.name if obj.primary_marketer else None

    @staticmethod
    def get_submission_count(obj):
        return obj.submissions.count()

    @staticmethod
    def get_current_city(obj):
        return obj.consultant.current_city

    @staticmethod
    def get_project_count(obj):
        return Project.objects.filter(submission__consultant_marketing=obj).count()

    @staticmethod
    def get_interview_count(obj):
        return Interview.objects.filter(
            submission__consultant_marketing=obj
        ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()


class ConsultantRateRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantRateRevision
        fields = '__all__'


class PayrollEmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollEmployer
        fields = ('id', 'name', 'start', 'created')


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


class ExitDetailConsultantSerializer(serializers.ModelSerializer):
    reasons = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantExit
        fields = ('id', 'created', 'type', 'status', 'rehire', 'created_by', 'last_date', 'resign_date', 'exit_details',
                  'reasons', 'notice_period', 'legal_action', 'legal_status', 'tagged_user', 'cancel_reason')

    @staticmethod
    def get_reasons(obj):
        return obj.reasons.all().values('id', 'name')

    @staticmethod
    def get_tagged_user(obj):
        return TaggedUserSerializer(obj.tagged_user.all(), many=True).data


class ExitConsultantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantExit
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
        fields = ('id', 'name', 'email', 'status', 'profiles', 'marketing_id', 'internal_employee', 'marital_status',
                  'timezone', 'country')

    @staticmethod
    def get_profiles(obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    @staticmethod
    def get_marketing_id(obj):
        queryset = obj.marketing.filter(status='open')
        if queryset:
            return queryset.first().id
        return None


class ConsultantV2ListSerializer(serializers.ModelSerializer):
    rate = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    retention = serializers.SerializerMethodField()
    work_auth = serializers.SerializerMethodField()
    visa_type = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()
    rate_revision = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'skills', 'status', 'marketing', 'recruiter', 'retention', 'rate', 'work_auth', 'exit',
                  'rate_revision', 'visa_type')

    @staticmethod
    def get_visa_type(obj):
        qs = obj.work_auth.filter(is_current=True)
        if qs:
            return qs.first().visa_type
        return None

    @staticmethod
    def get_rate(obj):
        qs = obj.rates.fliter(end=None)
        if qs:
            return qs.first().rate
        return None

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()

    @staticmethod
    def get_recruiter(obj):
        queryset = obj.pocs.filter(end=None, poc_type='recruiter')
        if queryset:
            return queryset.first().poc.employee_name
        return None

    @staticmethod
    def get_retention(obj):
        queryset = obj.pocs.filter(end=None, poc_type='retention')
        if queryset:
            return queryset.first().poc.employee_name
        return None

    @staticmethod
    def get_work_auth(obj):
        qs = obj.work_auth.filter(is_current=True)
        if qs:
            return {
                "visa_end": qs.first().visa_end,
                "visa_type": qs.first().visa_type,
                "visa_start": qs.first().visa_start,
            }
        return None

    @staticmethod
    def get_marketing(obj):
        qs = obj.marketing.filter(status='open')
        if qs:
            marketing = qs.last()
            return {
                "rtg": marketing.rtg,
                "start": marketing.start,
                "in_pool": marketing.in_pool,
                "preferred_location": marketing.preferred_location,
                "previous_marketing_days": marketing.previous_marketing_days,
            }
        return None

    @staticmethod
    def get_rate_revision(obj):
        qs = obj.rates.filter(end=None)
        if qs:
            revision_date = qs.first().start
        else:
            revision_date = date(2010, 1, 1)
        projects = Project.objects.filter(
            (
                    Q(consultant_id=obj.id) |
                    Q(submission__consultant_marketing__consultant_id=obj.id)
            ) & (
                Q(statuses__status='joined')
            )
        )
        for project in projects:
            if project.start_date:
                if revision_date < project.start_date:
                    revision_date = project.start_date
        if date.today() + timedelta(days=170) <= revision_date:
            return True
        return False


class ConsultantBenchSerializer(serializers.ModelSerializer):
    rate = serializers.ReadOnlyField()
    support = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    retention = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    work_auth = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    terminate = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    active_marketer = serializers.SerializerMethodField()
    payroll_employer = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'ssn', 'gender', 'phone_no', 'links', 'skills', 'skype', 'status',
                  'date_of_birth', 'work_type', 'current_city', 'is_w2', 'work_auth', 'recruiter', 'retention', 'rate',
                  'support', 'profiles', 'education', 'terminate', 'experience', 'marketing', 'payroll_employer',
                  'internal_employee', 'marital_status', 'active_marketer', 'timezone', 'country')

    @staticmethod
    def get_work_auth(obj):
        return WorkAuthSerializer(obj.work_auth.all(), many=True).data

    @staticmethod
    def get_profiles(obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    @staticmethod
    def get_education(obj):
        return EducationSerializer(obj.academics.all(), many=True).data

    @staticmethod
    def get_terminate(obj):
        return ExitDetailConsultantSerializer(obj.exit.all().order_by('-created'), many=True).data

    @staticmethod
    def get_experience(obj):
        return ExperienceSerializer(obj.experiences.all(), many=True).data

    @staticmethod
    def get_payroll_employer(obj):
        employers = obj.employers.all().order_by('-start')
        if employers:
            return PayrollEmployerSerializer(employers.first()).data
        return None

    @staticmethod
    def get_marketing(obj):
        marketing = obj.marketing.filter(status='open')
        if marketing:
            return ConsultantMarketingSerializer(marketing, many=True).data[0]
        else:
            return None

    @staticmethod
    def user_data(obj, user_obj):
        data = {
            "id": obj.id,
            'user_id': user_obj.id,
            'email': user_obj.email,
            'phone': user_obj.phone,
            'employee_name': user_obj.employee_name,
        }
        return data

    def get_recruiter(self, obj):
        queryset = obj.pocs.filter(end=None, poc_type='recruiter').first()
        if queryset:
            poc = queryset.poc
            return self.user_data(queryset, poc)
        return None

    def get_active_marketer(self, obj):
        queryset = obj.pocs.filter(end=None, poc_type='marketer').first()
        if queryset:
            poc = queryset.poc
            return self.user_data(queryset, poc)
        else:
            marketing = obj.marketing.filter(status='open').first()
            if marketing and marketing.primary_marketer:
                primary_marketer = marketing.primary_marketer
                return self.user_data(marketing, primary_marketer)
            else:
                return None

    def get_retention(self, obj):
        queryset = obj.pocs.filter(end=None, poc_type='retention').first()
        if queryset:
            poc = queryset.poc
            return self.user_data(queryset, poc)
        return None

    def get_support(self, obj):
        projects = Project.objects.filter(submission__consultant_marketing__consultant=obj)
        if projects:
            active_po = projects.filter(statuses__status='joined', statuses__is_current=True)
            if active_po:
                project = active_po.latest('start_date')
            else:
                project = projects.latest('start_date')

            queryset = project.support.all()
            if queryset:
                queryset = queryset.latest('start')
                poc = queryset.support
                return self.user_data(queryset, poc)
            return None
        return None


class ConsultantListSerializer(serializers.ModelSerializer):
    profiles = serializers.SerializerMethodField()

    @staticmethod
    def get_profiles(obj):
        return ConsultantProfileSerializer(obj.profiles.all(), many=True).data

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'profiles')


class ConsultantFeedbackSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = ('id', 'created', 'feedback_text', 'feedback_type', 'rating', 'consultant', 'created_by',
                  'tagged_user')

    @staticmethod
    def get_created_by(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_tagged_user(obj):
        return TaggedUserSerializer(obj.tagged_user.all(), many=True).data


class FeedbackSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()
    department = serializers.CharField(allow_null=True, allow_blank=True)

    class Meta:
        model = ConsultantFeedback
        fields = "__all__"

    @staticmethod
    def get_consultant(obj):
        return obj.consultant.name

    @staticmethod
    def get_created_by(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_project(obj):
        if obj.project:
            data = {
                'id': obj.project.id,
                'client_name': obj.project.submission.client,
                'vendor_name': obj.project.submission.vendor.name,
            }
            return data
        return None

    @staticmethod
    def get_tagged_user(obj):
        if obj.tagged_user:
            return TaggedUserSerializer(obj.tagged_user.all(), many=True).data
        return None


# Consultant Login
class MSAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MSAccount
        fields = '__all__'
