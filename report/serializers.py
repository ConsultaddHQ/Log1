from rest_framework import serializers

from employee.models import User
from marketing.models import Test
from project.models import Project

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


class TimesheetProjectSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    companies = serializers.SerializerMethodField()
    project_type = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'companies', 'display_name', 'project_type')

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
