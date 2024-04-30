from django.db.models import Q, F
from datetime import date, datetime
from rest_framework import serializers

from consultant.models import Consultant
from utils_app.aws_utils import get_s3_object
from employee.serializers import UserSerializer
from marketing.serializers import SubmissionSerializer
from project.utils import get_project_check_list, get_country
from attachment.serializers import AttachmentSerializer, AttachmentURLSerializer
from project.models import Project, ProjectOrder, ProjectSupport, SupportStatus, TimeSheet, PayrollSchedule, \
    ProjectStatus, ConsultantLeave, Leave, TimesheetRequest, TimetrackEvent, ProjectPaymentTerm, ProjectAssociates


class ProjectSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    work_type = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'created', 'submission', 'start_date', 'client', 'city', 'end_date', 'work_type',
                  'consultant_name', 'marketer_name', 'company_name', 'is_remote', 'check_list', 'employer', 'rate',
                  'duration')

    @staticmethod
    def get_created(obj):
        return obj.created

    @staticmethod
    def get_client(obj):
        return obj.submission.client

    @staticmethod
    def get_work_type(obj):
        return obj.submission.get_work_type_display()

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_company_name(obj):
        return obj.submission.lead.vendor_company.name

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)

    @staticmethod
    def get_consultant_name(obj):
        if obj.consultant:
            if obj.is_remote:
                firstname = obj.consultant.name.split(' ')[0] if obj.consultant else 'Not Assigned'
                return {
                    "remote": f"{firstname}", "name": f"{obj.submission.consultant.name}"
                }
            else:
                return {"name": obj.submission.consultant.name, "remote": obj.consultant.name.split(' ')[0]}
        return {"name": "Not Assigned"}


class PayrollScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollSchedule
        fields = '__all__'


class ProjectTimeSheetSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    work_type = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'client', 'start_date', 'employer', 'status', 'total_hours', 'work_type', 'timesheet_frequency')

    @staticmethod
    def get_status(obj):
        try:
            status = ProjectStatus.objects.get(project=obj, is_current=True)
            return status.status
        except ProjectStatus.DoesNotExist:
            return None

    @staticmethod
    def get_client(obj):
        char = ''
        status = ProjectStatus.objects.filter(project=obj, is_current=True).filter(
            Q(status='complete') | Q(status__istartswith='terminated')
        ).first()
        if status:
            char = '  '
        return obj.submission.client + (' (Timesheets)' + char if obj.submission.work_type == 'c2c' else ' (Paystubs)') + char

    @staticmethod
    def get_work_type(obj):
        return obj.submission.get_work_type_display()

    @staticmethod
    def get_total_hours(obj):
        total_hours = 0
        all_timesheet = TimeSheet.objects.filter(project=obj, hours__gt=0, status='approved')
        for timesheet in all_timesheet:
            total_hours = total_hours + int(timesheet.hours) + int(timesheet.additional_hours)
        return f"{total_hours}hrs"


class TimeSheetSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'remark', 'project', 'con_comment')

    @staticmethod
    def get_start(obj):
        return obj.start.strftime("%m/%d/%Y")

    @staticmethod
    def get_end(obj):
        return obj.end.strftime("%m/%d/%Y")

    @staticmethod
    def get_project(obj):
        return {
            'id': obj.project.id,
            'employer': obj.project.employer,
            'start_date': obj.project.start_date,
            'vendor': obj.project.submission.lead.vendor_company.name,
            'project_type': obj.project.submission.get_work_type_display(),
            'timesheet_frequency': obj.project.get_timesheet_frequency_display(),
            'client': obj.project.submission.client + (' (TimeSheets)' if obj.project.submission.work_type == 'c2c' else ' (PayStubs)'),
        }


class FinanceSerializer(serializers.ModelSerializer):
    submitted_at = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    class Meta:
        model = TimeSheet
        fields = ('id', 'start', 'end', 'status', 'hours', 'additional_hours', 'submitted_at', 'status_updated_at',
                  'status_updated_by', 'modified', 'attachments', 'remark', 'project', 'con_comment')

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
    def get_project(obj):
        return {
            'id': obj.project.id,
            'employer': obj.project.employer,
            'start_date': obj.project.start_date,
            'client': obj.project.submission.client,
            'vendor': obj.project.submission.lead.vendor_company.name,
            'work_type': obj.project.submission.get_work_type_display(),
        }


class ConsultantTimeSheetSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    ts_status = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'ts_status', 'project')

    @staticmethod
    def get_project(obj):
        project = obj.projects.all().latest('-start_date')
        if project:
            return {
                'id': project.id,
                'team': project.employer,
                'start_date': project.start_date,
                'client': project.submission.client,
                'vendor': project.submission.lead.vendor_company.name,
                'project_type': project.submission.get_work_type_display(),
            }
        return None

    @staticmethod
    def get_ts_status(obj):
        queryset = TimeSheet.objects.filter(project__consultant=obj)
        submitted_ts = True if queryset.filter(status__in=['submitted', 'updated']) else False
        rejected_ts = True if queryset.filter(status='rejected', is_active=True) else False
        draft_ts = True if queryset.filter(status='draft', is_active=True) else False
        return {'submitted': submitted_ts, 'rejected': rejected_ts, 'draft': draft_ts}


class ProjectGetSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    status = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'submission', 'feedback', 'check_list', 'attachments', 'created', 'city',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'rate', 'employer', 'reporting_details', 'is_remote', 'marketer_name')

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)


class SupportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportStatus
        fields = '__all__'


class ProjectSupportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSupport
        fields = '__all__'


class ProjectSupportSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        exclude = ('project',)

    @staticmethod
    def get_support(obj):
        return {
            'id': obj.support.id,
            'email': obj.support.email,
            'name': obj.support.employee_name,
        }

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return {
                "value": status.first().frequency,
                "change_date": status.first().change_date,
            }
        return None


class ProjectSupportDetailSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    technology = serializers.SerializerMethodField()
    frequency = serializers.SerializerMethodField()
    support = serializers.SerializerMethodField()
    joining_date = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = ('id', 'created', 'end', 'start', 'feedback', 'status', 'client', 'consultant', 'technology',
                  'support', 'joining_date', 'frequency')

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True).first()
        if obj.project.statuses.filter(status__istartswith='terminated').first():
            return 'terminated'
        elif obj.project.start_date and obj.project.start_date > date.today():
            return 'training'
        elif status:
            if status.frequency:
                return status.frequency
        else:
            return None

    @staticmethod
    def get_frequency(obj):
        status = obj.statuses.filter(is_current=True).first()
        if status:
            return status.frequency
        return None

    @staticmethod
    def get_client(obj):
        return obj.project.submission.client

    @staticmethod
    def get_support(obj):
        return UserSerializer(obj.support).data

    @staticmethod
    def get_technology(obj):
        return obj.project.submission.lead.primary_skill

    @staticmethod
    def get_joining_date(obj):
        return obj.project.start_date

    @staticmethod
    def get_consultant(obj):
        data = {
            'name': obj.project.consultant.name,
            'email': obj.project.consultant.email,
            'contact': obj.project.consultant.phone_no
        }
        return data


class ProjectOrderSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ProjectOrder
        fields = '__all__'

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.project.attachments.all(), many=True).data


class ConsultantLeaveSerializer(serializers.ModelSerializer):
    lapsed = serializers.SerializerMethodField()
    leave_type = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantLeave
        fields = ('id', 'granted', 'balance', 'leave_type', 'year', 'is_expired', 'on_hold', 'lapsed')

    @staticmethod
    def get_leave_type(obj):
        return obj.leave_type.display_name

    @staticmethod
    def get_lapsed(obj):
        total_leaves_consumed = 0
        consumed_leaves = Leave.objects.filter(
            leave_type__leave_type__name=obj.leave_type.name, consultant=obj.consultant, leave_type__year=date.today().year
        ).filter(status__in=['approved', 'pending', 'applied'])
        for leave in consumed_leaves:
            total_leaves_consumed += leave.total_hours
        lapsed = obj.granted - (obj.balance + total_leaves_consumed)
        return lapsed


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


class ProjectPaymentTermSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    payment_term_type = serializers.SerializerMethodField()

    class Meta:
        model = ProjectPaymentTerm
        fields = ('id', 'consultant_payment_term', 'payment_term', 'payment_term_type', 'comment', 'project')

    @staticmethod
    def get_project(obj):
        project = obj.project
        if project:
            return {
                'rate': project.rate,
                'project_id': project.id,
                'submission_id': project.submission.id,
                'client_name': project.submission.client,
                'remote_engineer': project.consultant.name,
                'project_type':project.submission.work_type,
                'country': get_country(project.submission.lead.city),
                'consultant_name': project.submission.consultant.name,
                'marketer_name': project.submission.created_by.employee_name,
                'vendor_company': project.submission.lead.vendor_company.name,
            }
        return None

    @staticmethod
    def get_payment_term_type(obj):
        return obj.get_payment_term_type_display()


class ProjectAssociatesSerializer(serializers.ModelSerializer):
    vp = serializers.SerializerMethodField()
    remote = serializers.SerializerMethodField()
    lead_sm = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    marketer = serializers.SerializerMethodField()
    team_lead = serializers.SerializerMethodField()
    recruiter = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    support_persons = serializers.SerializerMethodField()

    class Meta:
        model = ProjectAssociates
        fields = ('id', 'total_hours', 'initial_notification', 'secondary_notification', 'vp', 'interviews', 'lead_sm',
                  'team_lead', 'recruiter', 'marketer', 'support_persons', 'project', 'remote')

    @staticmethod
    def get_vp(obj):
        return {"employee_name": obj.vp.employee_name, "employee_id": obj.vp.employee_id}

    @staticmethod
    def get_lead_sm(obj):
        return {"employee_name": obj.lead_sm.employee_name, "employee_id": obj.lead_sm.employee_id} \
            if obj.lead_sm else {"employee_name": "Not Assigned", "employee_id": None}

    @staticmethod
    def get_remote(obj):
        return {
            "remote_consultant": obj.project.consultant.name,
            "is_remote": obj.project.is_remote, "con_id": obj.project.consultant_id
        }

    @staticmethod
    def get_team_lead(obj):
        return {"employee_name": obj.team_lead.employee_name, "employee_id": obj.team_lead.employee_id} \
            if obj.team_lead else {"employee_name": "Not Assigned", "employee_id": None}

    @staticmethod
    def get_marketer(obj):
        return {"employee_name": obj.marketer.employee_name, "employee_id": obj.marketer.employee_id}

    @staticmethod
    def get_recruiter(obj):
        return {"employee_name": obj.recruiter.employee_name, "employee_id": obj.recruiter.employee_id}\
            if obj.recruiter else {"employee_name": "Not Assigned", "employee_id": None}

    @staticmethod
    def get_duration(support):
        start_date = support.start
        end_date = support.end
        if end_date:
            diff = end_date - start_date
        elif start_date > date.today():
            return "Not Started"
        else:
            diff = date.today() - start_date

        months = diff.days // 30  # Assuming an average of 30 days per month
        days = diff.days % 30
        if months > 0 and days > 0:
            return f"{months} months and {days} days"
        elif months > 0:
            return f"{months} months"
        else:
            return f"{days} days"

    @staticmethod
    def get_support_persons(obj):
        support_info = []
        for support in obj.support_persons.all():
            frequency = support.statuses.filter(is_current=True).first()
            support_info.append(
                {
                    "start": support.start, "end": support.end,
                    "support_person_emp_id": support.support.employee_id,
                    "duration": ProjectAssociatesSerializer.get_duration(support),
                    "id": support.id, "support_name": support.support.employee_name,
                    "status": " ".join(frequency.frequency.split("_")).capitalize() if frequency else None
                }
            )
        return support_info

    @staticmethod
    def get_interviews(obj):
        interview_info = [
            {
                f'round': interview.round, "id": interview.id,
                'supervisor': {
                    "emp_id": interview.supervisor.employee_id,
                    "name": interview.supervisor.employee_name
                    if interview.supervisor.employee_id != 9999 else f"Consultant - {interview.consultant.name}"
                },
                'coders': list(
                    interview.guests.filter(type__in=['Assistant', 'Coder', 'Coder & Assistant']).annotate(
                        employee_name=F('user__employee_name'), employee_id=F('user__employee_id')
                    ).values('employee_name', 'employee_id')
                )
            } for interview in obj.interviews.all().order_by('id').distinct('id')
        ]
        return interview_info

    @staticmethod
    def get_project(obj):
        joining_date = obj.project.statuses.filter(is_current=True, status='joined').first()
        data = {
            "id": obj.project_id,
            "start_date": obj.project.start_date,
            "client": obj.project.submission.client,
            "submission_id": obj.project.submission_id,
            "name": obj.project.submission.consultant.name,
            "email": obj.project.submission.consultant.email,
            "type": obj.project.submission.get_work_type_display(),
            "vendor": obj.project.submission.lead.vendor_company.name,
            "joining_date": joining_date.created.strftime("%Y-%m-%d") if joining_date else "Not Joined",
            "job_title": obj.project.submission.lead.position.display_name
            if obj.project.submission.lead.position else None
        }
        return data
