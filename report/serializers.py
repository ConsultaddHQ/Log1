from rest_framework import serializers

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
    companies = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'companies')

    @staticmethod
    def get_companies(obj):
        submission = obj.submission
        if submission:
            return {
                'client': submission.client,
                'vendor': submission.lead.vendor_company.name
            }
        return None


class TimesheetTestSerializer(serializers.ModelSerializer):
    test_id = serializers.IntegerField(source='id')
    companies = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('test_id', 'companies', 'consultant')

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
