from rest_framework import serializers


class ReportSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sub_id = serializers.SerializerMethodField()

    def get_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.submission.id if model in ['Interview', 'Project'] else obj.id
        return None
    def get_name(self, obj):
        model = self.context.get('model')
        if obj:
            if model == 'Consultant':
                return obj.name
            elif model in ['Submission', 'Interview', 'Project']:
                return obj.consultant.name
            else:
                return None
        return None

    def get_sub_id(self, obj):
        model = self.context.get('model')
        if obj:
            return obj.id if model in ['Interview', 'Project'] else None
        return None
