from rest_framework import serializers

from dashboard.models import QuickActions


class QuickActionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickActions
        fields = '__all__'
