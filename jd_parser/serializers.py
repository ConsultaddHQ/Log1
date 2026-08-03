from rest_framework import serializers

from jd_parser.models import MarketingMail, MMailScrap


class MarketingMailListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MMailScrap
        fields = [
            "id",
            "sender_mail",
            "sender_name",
            "body_text",
            "snippet",
            "subject",
            "date",
            "keywords",
            "requirementMail"
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["keywords"] = instance.keywords.split(";")
        return representation


class MarketingMailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MMailScrap
        fields = (
            "id",
            "sender_mail",
            "sender_name",
            "snippet",
            "subject",
            "date",
            "body_text",
            "body_html",
            "keywords",
            "marketer_feedback"
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["keywords"] = instance.keywords.split(";")
        return representation
