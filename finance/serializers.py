from rest_framework import serializers
from utils_app.aws_utils import get_s3_object
from attachment.serializers import AttachmentURLSerializer
from project.models import Project, TimetrackEvent, TimeSheet, Leave, TimesheetRequest


class FinanceSerializer(serializers.ModelSerializer):
    consultant = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    project_status = serializers.SerializerMethodField()
    timesheet_status = serializers.SerializerMethodField()
    request_timesheet = serializers.SerializerMethodField()

    class Meta:
        model = Project
        ref_name = 'FinanceProject'
        fields = ('id', 'employer', 'start_date', 'project_status', 'timesheet_status', 'request_timesheet',
                  'timesheet_frequency', 'consultant', 'submission')

    def get_timesheet_status(self, obj):
        status = self.context.get('timesheet_status')
        if status:
            return status[0]
        ts_obj = TimeSheet.objects.filter(project=obj)
        try:
            if ts_obj.filter(status__in=["updated", "submitted"]):
                return "pending"
            elif ts_obj.filter(status="rejected"):
                return "rejected"
            elif ts_obj.filter(status="approved"):
                return "approved"
            elif ts_obj.filter(status="draft") & self.context.get('timesheet'):
                return "draft"
            else:
                return None
        except:
            ts_status = None
        return ts_status

    @staticmethod
    def get_project_status(obj):
        if obj.statuses.filter(status__istartswith='terminated').first():
            return "terminated"
        return obj.status

    @staticmethod
    def get_request_timesheet(obj):
        return True if TimesheetRequest.objects.filter(project=obj, status="request") else False

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
        consultant=obj.consultant
        return {
            'id': consultant.id,
            'name': consultant.name,
            'email': consultant.email,
        }


class FinanceDetailSerializer(serializers.ModelSerializer):
    end = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
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
        if obj.status == "updated" or obj.status == "submitted":
            return "pending"
        return obj.status

    @staticmethod
    def get_status(obj):
        if obj.status=="submitted":
            return "pending"
        return obj.status


class LeaveSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    leave_type = serializers.SerializerMethodField()
    attachment = serializers.SerializerMethodField()
    duration_type = serializers.SerializerMethodField()

    class Meta:
        model = Leave
        ref_name = 'FinanceLeave'
        fields = ('id', 'leave_type', 'to_date', 'from_date', 'total_hours', 'applied_on', 'status',
                  'description', 'attachment', 'duration_type', "remarks")

    @staticmethod
    def get_status(obj):
        return obj.get_status_display()

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
    end = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()

    class Meta:
        model = TimesheetRequest
        ref_name = 'FinanceTimesheetRequest'
        fields = ('id', 'start', 'end', 'status', 'submitted_at', 'attachments', 'reviewer_comment',
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
        if obj.status == "request":
            return "pending"
        elif obj.status == "reject":
            return "rejected"
        elif obj.status == "accepted":
            return "approved"
        else:
            return None

    @staticmethod
    def get_attachments(obj):
        return AttachmentURLSerializer(obj.attachments.filter(is_active=True), many=True).data


class TimetrackEventSerializer(serializers.ModelSerializer):
    consultants = serializers.SerializerMethodField()

    class Meta:
        model = TimetrackEvent
        ref_name = 'FinanceTimetrackEvent'
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
