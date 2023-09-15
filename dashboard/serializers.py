from rest_framework import serializers

from dashboard.models import QuickActions


class QuickActionsViewSetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickActions
        fields = '__all__'
