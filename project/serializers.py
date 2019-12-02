from rest_framework import serializers

from project.models import *
from marketing.serializers import InterviewGetSerializer, SubmissionSerializer
from attachment.serializers import AttachmentSerializer


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class ProjectGetSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    interview = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'submission', 'feedback', 'check_list', 'attachments', 'interview', 'created',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'reporting_details')

    @staticmethod
    def get_attachments(self):
        return AttachmentSerializer(self.attachments.all(), many=True).data

    @staticmethod
    def get_interview(self):
        return InterviewGetSerializer(self.submission.screening.all(), many=True).data

    @staticmethod
    def get_check_list(self):
        msa, client_address, vendor_address, work_order, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0, 0, 0

        start_date = 1 if self.start_date else 0

        if self.attachments.filter(attachment_type='msa'):
            msa = 1

        if self.attachments.filter(attachment_type='work_order'):
            work_order = 1

        if self.attachments.filter(attachment_type='work_order_msa'):
            msa, work_order = 1, 1

        if self.attachments.filter(attachment_type='msa_signed'):
            s_msa = 1

        if self.attachments.filter(attachment_type='work_order_signed'):
            s_work_order = 1

        if self.attachments.filter(attachment_type='work_order_msa_signed'):
            s_msa, s_work_order = 1, 1

        if self.client_address and len(self.client_address.strip()) > 0:
            client_address = 1

        if self.vendor_address and len(self.vendor_address.strip()) > 0:
            vendor_address = 1

        if self.reporting_details and len(self.reporting_details.strip()) > 0:
            reporting_details = 1

        status = True if (s_msa + s_work_order + client_address + vendor_address + start_date + reporting_details
                          ) / 6 >= 1 else False

        return {"status": status, "total": 6, "msa": msa, "work_order": work_order, "client_address": client_address,
                "vendor_address": vendor_address, "start_date": start_date, "reporting_details": reporting_details,
                "msa_signed": s_msa, "work_order_signed": s_work_order}
