from rest_framework import serializers

from project.models import *
from marketing.models import *
from employee.models import User
from attachment.serializers import AttachmentSerializer


class VendorCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCompany
        fields = '__all__'


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    vendor_company_name = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()

    @staticmethod
    def get_vendor_company_name(self):
        return self.vendor_company.name if self.vendor_company else None

    @staticmethod
    def get_marketer(self):
        return self.marketer.employee_name

    class Meta:
        model = Lead
        fields = (
            'id', 'job_desc', 'job_title', 'skill', 'location', 'vendor_company_id', 'vendor_company_name', 'marketer',
            'status', 'created', 'modified')
