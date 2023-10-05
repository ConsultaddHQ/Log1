from rest_framework import serializers
from utils_app.aws_utils import get_s3_object
from attachment.serializers import AttachmentURLSerializer
from project.models import Project, TimetrackEvent, TimeSheet, Leave, TimesheetRequest


class FinanceSerializer(serializers.ModelSerializer):
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    project_status = serializers.SerializerMethodField()
    timesheet_status = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'employer', 'start_date','project_status','timesheet_status','consultant', 'submission')

    @staticmethod
    def get_timesheet_status(obj):
        ts_obj = TimeSheet.objects.filter(project=obj, status__in=["updated", "submitted"])
        try:
            ts_status = ts_obj.latest().status if ts_obj else TimeSheet.objects.filter(
                project=obj).latest().status
        except:
            ts_status = None
        return ts_status

    @staticmethod
    def get_project_status(obj):
        if obj.statuses.filter(status__istartswith='terminated').first():
            return "terminated"
        return obj.status

    @staticmethod
    def get_submission(obj):
        submission = obj.submission
        return {
            "client": submission.client,
            "vendor": submission.lead.vendor_company.name,
            "job_type": submission.get_work_type_display(),
            "consultant": {
                "id": submission.consultant_marketing.consultant.id,
                "name": submission.consultant_marketing.consultant.name
            },
        }

    @staticmethod
    def get_consultant(obj):
        # consultant = obj.submission.consultant_marketing.consultant
        consultant=obj.consultant
        return {
            'id': consultant.id,
            'name': consultant.name,
            'email': consultant.email,
        }


class FinanceDetailSerializer(serializers.ModelSerializer):
    end = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    # project = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    list_page_status = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'list_page_status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'attachments', 'remark', 'con_comment')

    @staticmethod
    def get_submitted_at(obj):
        if obj.submitted_at:
            return obj.submitted_at.date()
        return None

    @staticmethod
    def get_start(obj):
        return obj.start.strftime("%m/%d/%Y")

    @staticmethod
    def get_end(obj):
        return obj.end.strftime("%m/%d/%Y")

    @staticmethod
    def get_attachments(obj):
        return AttachmentURLSerializer(obj.attachments.filter(is_active=True), many=True).data

    @staticmethod
    def get_list_page_status(obj):
        if obj.status=="updated" or obj.status=="submitted":
            return "pending"
        return obj.status

    # @staticmethod
    # def get_project(obj):
    #     submission = obj.project.submission
    #     return {
    #         'id': obj.project.id,
    #         'employer': obj.project.employer,
    #         'start_date': obj.project.start_date,
    #         'submission' : {
    #             'client': submission.client,
    #             'vendor': submission.lead.vendor_company.name,
    #             'work_type': submission.get_work_type_display(),
    #         }
    #     }


class LeaveSerializer(serializers.ModelSerializer):
    leave_type = serializers.SerializerMethodField()
    attachment = serializers.SerializerMethodField()
    duration_type = serializers.SerializerMethodField()

    class Meta:
        model = Leave
        fields = ('id', 'leave_type', 'to_date', 'from_date', 'total_hours', 'applied_on', 'status',
                  'description', 'attachment', 'duration_type')

    @staticmethod
    def get_leave_type(obj):
        return obj.leave_type.leave_type.display_name

    @staticmethod
    def get_attachment(obj):
        data = []
        attachment = obj.attachment.first()
        if attachment:
            response, error = get_s3_object(attachment.attachment_file.name)
            if error:
                return []
            extension = attachment.attachment_file.name.split(".")[-1]
            data.append({
                "id": attachment.id, "file_path": response, "extension": extension,
                "created": attachment.created,"file_name": attachment.filename,
            })
        return data

    @staticmethod
    def get_duration_type(obj):
        if obj.total_hours == 8:
            return 'Full'
        elif obj.total_hours == 4:
            return 'Half'
        elif obj.total_hours % 8 == 0:
            return 'Multi Day'
        elif obj.total_hours:
            return 'Hourly'


class TimesheetRequestSerializer(serializers.ModelSerializer):
    submitted_at = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimesheetRequest
        fields = ('id', 'start', 'end', 'status', 'submitted_at', 'attachments', 'project', 'reviewer_comment',
                  'consultant_comment', 'reviewed_by')

    @staticmethod
    def get_submitted_at(obj):
        if obj.created:
            return obj.created.date()
        return None

    @staticmethod
    def get_reviewed_by(obj):
        if obj.reviewed_by:
            return obj.reviewed_by.employee_name
        return None

    @staticmethod
    def get_start(obj):
        return obj.start.strftime("%m/%d/%Y")

    @staticmethod
    def get_end(obj):
        return obj.end.strftime("%m/%d/%Y")

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()

    @staticmethod
    def get_attachments(obj):
        return AttachmentURLSerializer(obj.attachments.filter(is_active=True), many=True).data

    @staticmethod
    def get_project(obj):
        return {
            'id': obj.project.id,
            'employer': obj.project.employer,
            'start_date': obj.project.start_date,
            'client': obj.project.submission.client,
            'vendor': obj.project.submission.lead.vendor_company.name,
        }


class TimetrackEventSerializer(serializers.ModelSerializer):
    consultants = serializers.SerializerMethodField()

    class Meta:
        model = TimetrackEvent
        fields = ('id', 'start', 'end', 'title', 'description', 'action_link', 'event_type', 'image',
                  'feedback_type', 'consultants', 'is_active')

    @staticmethod
    def get_consultants(obj):
        consultants = obj.consultants.all().values('id', 'name')
        data = {
            "consultants": consultants,
            "all": True if len(consultants) > 50 else False
        }
        return data