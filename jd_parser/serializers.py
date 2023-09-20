from rest_framework import serializers

from jd_parser.models import MarketingMail, MMailScrap


class MarketingMailListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MMailScrap
        fields = ["id", "sender_mail", "sender_name", "snippet", "subject", "date"]


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
        )
