
from rest_framework import serializers

from dashboard.models import QuickActions


class QuickActionSerializer(serializers.ModelSerializer):
    add_consultants = serializers.SerializerMethodField()
    search_consultant = serializers.SerializerMethodField()

    class Meta:
        model = QuickActions
        fields = ('id', 'add_consultants', 'search_consultant')

    @staticmethod
    def get_add_consultants(obj):
        result = [
            {'id': consultant.id, 'name': consultant.name}
            for consultant in obj.add_consultants.all()
        ]
        result.reverse()
        return {
            'count': obj.add_consultants.count(),
            'consultants': result,
        }

    @staticmethod
    def get_search_consultant(obj):
        result = [
            {'id': consultant.id, 'name': consultant.name}
            for consultant in obj.search_consultants.all()
        ]
        result.reverse()
        return {
            'count': obj.search_consultants.count(),
            'consultants': result,
        }

