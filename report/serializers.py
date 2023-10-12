from rest_framework import serializers

CHECK_FOR_NAME = ['Submission', 'Interview', 'Project']
CHECK_FOR_ID = ['Interview', 'Project']


class ReportSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sub_id = serializers.SerializerMethodField()

    def get_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.submission.id if model in CHECK_FOR_ID else obj.id
        return None

    def get_name(self, obj):
        model = self.context.get('model')
        if obj:
            if model == 'Consultant':
                return obj.name
            elif model in CHECK_FOR_NAME:
                return obj.consultant.name if obj.consultant else None
            else:
                return None
        return None

    def get_sub_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.id if model in CHECK_FOR_ID else None
        return None
