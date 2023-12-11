from rest_framework import serializers

from employee.models import User
from project.models import Project, ProjectSupport
from consultant.models import Consultant
from marketing.models import Submission, Interview, Test

CHECK_FOR_NAME_FIELD = ['Submission', 'Interview', 'Project']
CHECK_FOR_ID_FIELD = ['Interview', 'Project']


class ReportSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sub_id = serializers.SerializerMethodField()

    def get_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.submission.id if model in CHECK_FOR_ID_FIELD else obj.id
        return None

    def get_name(self, obj):
        model = self.context.get('model')
        if obj:
            if model == 'Consultant':
                return obj.name
            elif model in CHECK_FOR_NAME_FIELD:
                return obj.consultant.name if obj.consultant else None
            else:
                return None
        return None

    def get_sub_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.id if model in CHECK_FOR_ID_FIELD else None
        return None


class ConsultantInfoSerializer(serializers.ModelSerializer):
    rate = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    visa_type = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'skills', 'status', 'marketing', 'recruiter', 'rate', 'visa_type')

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
    def get_marketing(obj):
        qs = obj.marketing.filter(status='open')
        if qs:
            marketing = qs.last()
            return {
                "preferred_location": marketing.preferred_location,
                "previous_marketing_days": marketing.previous_marketing_days
            }
        return None


class SubmissionInfoSerializer(serializers.ModelSerializer):
    vendor = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ('id', 'consultant', 'marketer', 'client', 'vendor', 'rate',  'is_complete', 'created')

    @staticmethod
    def get_consultant(obj):
        return obj.consultant.name

    @staticmethod
    def get_marketer(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_vendor(obj):
        return obj.vendor.name if obj.vendor else None


class InterviewInfoSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    interview_mode = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = ('id', 'consultant', 'marketer', 'submission', 'start_time', 'round', 'supervisor',
                  'interview_mode', 'status')

    @staticmethod
    def get_consultant(obj):
        return obj.consultant.name

    @staticmethod
    def get_marketer(obj):
        return obj.marketer.employee_name

    @staticmethod
    def get_supervisor(obj):
        return obj.supervisor.employee_name

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()

    @staticmethod
    def get_interview_mode(obj):
        return obj.get_interview_mode_display()

    @staticmethod
    def get_submission(obj):
        submission = obj.submission
        return {
            "sub_id": submission.id,
            "client": submission.client,
            "title": submission.lead.job_title,
            "vendor": submission.vendor.name if submission.vendor else None,
            "position": submission.lead.position.display_name if submission.lead.position else None
        }


class ProjectInfoSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    project_type = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'consultant', 'marketer', 'submission', 'rate', 'status', 'project_type', 'is_remote',
                  'start_date')

    @staticmethod
    def get_marketer(obj):
        return obj.marketer_name

    @staticmethod
    def get_project_type(obj):
        return obj.submission.get_work_type_display()

    @staticmethod
    def get_status(obj):
        return obj.status

    @staticmethod
    def get_submission(obj):
        submission = obj.submission
        return {
            "sub_id": submission.id, "client": submission.client,
            "vendor": submission.vendor.name if submission.vendor else None,
            "position": submission.lead.position.display_name if submission.lead.position else None
        }

    @staticmethod
    def get_consultant(obj):
        if obj.is_remote:
            firstname = obj.consultant.name.split(' ')[0] if obj.consultant else 'Not Assigned'
            return {
                "remote": f"{firstname}", "name": f"{obj.submission.consultant.name}"
            }
        else:
            return {"name": obj.submission.consultant.name, "remote": obj.consultant.name.split(' ')[0]}


class TimesheetProjectSerializer(serializers.ModelSerializer):
    support = serializers.SerializerMethodField()
    companies = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    project_type = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'companies', 'display_name', 'project_type', 'support')

    @staticmethod
    def get_companies(obj):
        submission = obj.submission
        if submission:
            return {
                'client': submission.client,
                'vendor': submission.lead.vendor_company.name
            }
        return None

    @staticmethod
    def get_display_name(obj):
        return f'{obj.id}:{obj.submission.client}'

    def get_support(self, obj):
        if self.context.get('employee_id'):
            return ProjectSupport.objects.filter(
                project=obj, support__employee_id=self.context.get('employee_id')
            ).values('start', 'end')
        return {}

    def get_project_type(self, obj):
        return self.context.get('project_type')


class TimesheetTestSerializer(serializers.ModelSerializer):
    test_id = serializers.IntegerField(source='id')
    companies = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    submit_date = serializers.SerializerMethodField()
    assign_to = serializers.SerializerMethodField()
    submit_month = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('test_id', 'companies', 'consultant', 'submit_date', 'assign_to', 'submit_month')

    @staticmethod
    def get_companies(obj):
        submission = obj.submission
        if submission:
            return {
                'client': submission.client,
                'vendor': submission.lead.vendor_company.name
            }
        return None

    @staticmethod
    def get_consultant(obj):
        consultant = obj.submission.consultant if obj.submission else None
        return {
            'id': consultant.id,
            'name': consultant.name
        }

    @staticmethod
    def get_submit_date(obj):
        if obj.submit_date:
            return obj.submit_date.date()
        return None

    @staticmethod
    def get_assign_to(obj):
        engineers = obj.assign_to.all()
        data = []
        if engineers:
            for engineer in engineers:
                data.append({'employee_id': engineer.employee_id, 'name': engineer.employee_name})
            return data
        return None

    @staticmethod
    def get_submit_month(obj):
        submit_date = obj.submit_date
        if submit_date:
            return f'{submit_date.date().year}-{str(submit_date.date().month).zfill(2)}'
        return None


class TimesheetUserSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('employee_name', 'email', 'team')

    @staticmethod
    def get_team(obj):
        team = obj.team
        if team:
            return {
                'name': team.name,
                'department': team.dept
            }
        return None
