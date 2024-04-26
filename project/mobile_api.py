import os
from datetime import datetime, timedelta, date

from django.utils import timezone
from django.db.models import Q, Max
from django.shortcuts import get_object_or_404
from dateutil.relativedelta import relativedelta

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from django.contrib.contenttypes.models import ContentType
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin

from constance import config

from employee.models import User
from attachment.models import Attachment
from consultant.models import Consultant
from utils_app.thred_mail import send_email
from log1.utils import write_exception, ERROR_MSG
from consultant.permissions import ConsultantIsAuthenticated
from utils_app.aws_utils import get_s3_object, download_s3_object
from consultant.authentication import ConsultantTokenAuthentication
from notification.utils import create_notification, push_notification
from project.utils import check_days, mark_in_active
from project.models import Project, TimeSheet, PayrollSchedule, ConsultantLeave, Leave, TimesheetRequest, \
    TimetrackEvent, TimetrackEventFeedback
from project.serializers import TimeSheetSerializer, PayrollScheduleSerializer, ProjectTimeSheetSerializer, \
    ConsultantLeaveSerializer, LeaveSerializer, TimetrackEventSerializer


# Route - /payroll/
class PayrollScheduleViewSet(ListModelMixin, GenericViewSet):
    queryset = PayrollSchedule.objects.all()
    serializer_class = PayrollScheduleSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            queryset = PayrollSchedule.objects.filter(pay_date__year=datetime.today().year).order_by('id')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


# Route - /timesheet/
class TimeSheetViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @staticmethod
    def create_timesheet(obj, start_date=None, frequency=None, count=2):
        if not start_date:
            start_date = obj.start_date
        week_day = start_date.weekday()
        if week_day == 6:
            start_date = start_date + timedelta(days=1)
            week_day = start_date.weekday()
        if obj.submission.work_type == 'C2C':
            days = 6
        elif frequency == 'Biweekly':
            days = 13
        else:
            days = 6

        if frequency == 'Monthly':
            end_date = start_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        elif week_day == 0:
            end_date = start_date + timedelta(days=days)
        else:
            end_date = start_date + timedelta(days=days - week_day)

        for i in range(count):
            TimeSheet.objects.get_or_create(
                start=start_date, end=end_date,
                hours=0, status='draft', project=obj,
            )
            start_date = end_date + timedelta(days=1)
            end_date = end_date + timedelta(days=days + 1)

    def list(self, request, *args, **kwargs):
        try:
            projects = Project.objects.filter(
                Q(consultant=request.user, statuses__is_current=True) & (
                        Q(statuses__status='joined') |
                        Q(statuses__status__istartswith='terminated') |
                        Q(statuses__status__in=['complete', 'extended'])
                )
            ).order_by('-start_date')

            serializer = ProjectTimeSheetSerializer(projects, many=True)
            return Response({'result': serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'), consultant=request.user)
            queryset = TimeSheet.objects.filter(
                project=project, status__in=['draft', 'rejected'], is_active=True
            ).order_by('end')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='frequency')
    def frequency(self, request, pk):
        try:
            project = get_object_or_404(Project, id=pk, consultant=request.user)
            data = {
                "timesheet": hasattr(project, 'timesheets'),
                "project_type": project.submission.work_type,
                "timesheet_frequency": project.get_timesheet_frequency_display(),
            }
            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['POST'], detail=True, url_path='set_frequency')
    def frequency(self, request, pk):
        try:
            frequency = request.data['frequency']
            project = get_object_or_404(Project, id=pk, consultant=request.user)
            project.timesheet_frequency = frequency
            project.save()
            prev_timesheet = TimeSheet.objects.filter(project=project).order_by('-created')
            # if prev_timesheet:
            #     if prev_timesheet.exclude(status='draft').exists():
            #         last_filled_timesheet = prev_timesheet.exclude(status='draft').first()
            #         draft_timesheet = prev_timesheet.filter(status='draft', start__gte=last_filled_timesheet.end)
            #         timesheet_start_date = draft_timesheet.last().start if draft_timesheet else last_filled_timesheet.end + timedelta(days=1)
            #         draft_timesheet.delete()
            #         self.create_timesheet(project, timesheet_start_date, frequency)
            #     else:
            #         timesheet_start_date = prev_timesheet.last().start
            #         prev_timesheet.delete()
            #         self.create_timesheet(project, timesheet_start_date, frequency)
            # else:
            #     self.create_timesheet(project, frequency=frequency)

            return Response({"message": "Timesheet frequency updated successfully"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def create(self, request):
        try:
            screenshot = False
            perv_attachments = request.data.get('attachments', None)
            if perv_attachments is not None:
                perv_attachments = list(perv_attachments.split(","))
            else:
                perv_attachments = []
            week_id = request.data.get('week_id', None)
            zero_hours = request.GET.get('zero_hours', None)
            project_id = request.data.get('project_id', None)
            project = get_object_or_404(Project, id=project_id)

            if project.submission.work_type != "c2c":
                start = request.data['start_week']
                start = datetime.strptime(start, "%Y-%m-%d").date()
                end = request.data['end_week']
                end = datetime.strptime(end, "%Y-%m-%d").date()
                if week_id and week_id != '0':
                    timesheet = TimeSheet.objects.filter(id=week_id,project=project,status__in=["submitted", "rejected"]).first()
                    timesheet.start = start
                    timesheet.end = end
                else:
                    query = Q(project=project, end__gte=start, start__lte=start) | Q(project=project,end__gte=end,start__lte=end)
                    available_timesheet = TimeSheet.objects.filter(query).exclude(status="draft").order_by('-created')
                    if available_timesheet:
                        timesheet = available_timesheet.first()
                        available_week = f"{timesheet.start} - {timesheet.end}"
                        return Response({"error": f"PayStubs already exist {available_week}"}, status=400)

                    timesheet = TimeSheet.objects.create(
                        start=start, end=end, project=project, status='request',
                    )
                # update_timesheet = TimeSheet.objects.filter(project=project, start=start, end=end,
                #                                           status__in=["submitted", "rejected"])

            else:
                timesheet = get_object_or_404(
                    TimeSheet, id=request.data.get('week_id', None),
                    project__consultant=request.user,
                    status__in=['draft', 'rejected', 'submitted'],
                    is_active=True,
                )
            if not timesheet:
                return Response({"error": "SOMETHING WENT WRONG"}, status=400)

            timesheet_id = timesheet.id
            hours = float(request.data.get('hours'))
            timesheet.status = 'submitted' if timesheet.status != 'submitted' else 'updated'
            if zero_hours:
                timesheet.hours = 0.0
                timesheet.additional_hours = 0.0
                screenshot = True
            else:
                timesheet.hours = hours if hours < 41.0 else 40.0
                timesheet.additional_hours = 0.0 if hours < 41.0 else hours - 40.0
            timesheet.con_comment = request.data.get('comment')

            # Uploading Timesheet Screenshots to S3
            try:
                content_type = ContentType.objects.get(model='timesheet')
                if request.FILES.get('file1', None):
                    attachments = Attachment.objects.filter(object_id=timesheet.id, is_active=True,
                                                            attachment_type='timesheet')
                    for attachment in attachments:
                        if str(attachment.id) in perv_attachments:
                            continue
                        attachment.is_active = False
                        attachment.save()

                    Attachment.objects.create(
                        creator_id=1,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file1'),
                    )
                    screenshot = True
                if request.FILES.get('file2', None):
                    Attachment.objects.create(
                        creator_id=1,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file2'),
                    )
                    screenshot = True
                if perv_attachments:
                    screenshot = True
                if not screenshot:
                    return Response({"error": "Attachment is required"}, status=400)
            except Exception as error:
                write_exception(error, request)
                return Response({"error": str(error)}, status=400)

            timesheet.submitted_at = datetime.now()
            timesheet.save()

            last_timesheet = TimeSheet.objects.filter(project=timesheet.project).aggregate(Max('end'))
            end_date = last_timesheet['end__max']
            if project.submission.work_type == "c2c":
                self.create_timesheet(
                    timesheet.project, end_date + timedelta(days=1), timesheet.project.timesheet_frequency, count=1
                )
            # new_ts, created = TimeSheet.objects.get_or_create(
            #     project=timesheet.project,
            #     start=end_date + timedelta(days=1),
            #     end=end_date + timedelta(days=7),
            # )
            # if created:
            #     new_ts.hours = 0
            #     new_ts.save()

            user_list = User.objects.filter(Q(role__name='finance'))
            title = f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}"
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "timesheet",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'timesheet',
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }

            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)
            # timesheet_submission_mail(timesheet, request)

            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data, "timesheet_id": timesheet_id}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, pk):
        try:
            if pk == 'null' or pk is None:
                return Response({"error": "Project not found"}, status=400)

            submitted = TimeSheet.objects.filter(
                project_id=pk, is_active=True,
                status__in=['submitted', 'rejected', 'approved', 'updated']
            ).order_by('-start')
            serializer = self.serializer_class(submitted, many=True)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['POST'], detail=False, url_path='contact_us')
    def contact_us(self, request):
        message = request.data.get('message')
        contact_type = request.data.get('type')
        phone_type = request.data.get('device_type', None)
        try:
            if contact_type == 'finance':
                to = ['finance@consultadd.com']
                subject = f'Timesheet app issue from {request.user.name} :: {str(datetime.now())}'
                bcc = [config.APP_ADMIN, os.environ.get('DEVELOPER_EMAIL'), os.environ.get('PROJECT_OWNER')]
            elif contact_type == 'support':
                to = [config.APP_ADMIN, config.TIMESHEET_APP_ADMIN]
                bcc = [os.environ.get('DEVELOPER_EMAIL'), os.environ.get('PROJECT_OWNER')]
                subject = f'Bug Report from :: {request.user.email} :: {phone_type} :: {str(datetime.now())}'
            else:
                return Response({"result": "Select correct option"}, status=400)

            if os.environ.get('ENV', 'local') != 'prod':
                to = [config.APP_ADMIN]
                subject += "Development server"
                bcc = [os.environ.get('TIMESHEET_DEVELOPER_EMAIL')]

            mail_data = {
                'subject': subject,
                'to': to, 'cc': [], 'bcc': bcc,
                'template': '../templates/timesheet_contact_us.html',
                'context': {
                    "consultant_name": request.user.name,
                    "consultant_email": request.user.email,
                    "message": message,
                },
            }
            send_email(mail_data, 'timesheet@consultadd.com', request=request)

            user_list = User.objects.filter(role__name='finance')
            title = f"{request.user.name} has Timesheet issue, please check mail."
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "consultant",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://log1.app/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'app_issue',
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)

            return Response({"result": "mail sent"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['PUT'], detail=True, url_path='cancel')
    def cancel_timesheet(self, request, pk):
        try:
            queryset = TimeSheet.objects.filter(
                id=pk, project__consultant=request.user,
                status__in=['submitted', 'updated'],
            )
            if not queryset:
                return Response({"error": "Timesheet not found"}, status=404)

            timesheet = queryset.first()
            timesheet.hours = 0
            timesheet.status = 'draft'
            timesheet.con_comment = None
            timesheet.additional_hours = 0
            timesheet.save()
            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='attachments')
    def attachments(self, request, pk):
        try:
            timesheet = get_object_or_404(TimeSheet, id=pk, project__consultant=request.user)
            if timesheet.status == 'rejected':
                timesheet = TimeSheet.objects.filter(
                    project_id=timesheet.project.id, is_active=True,
                    end=timesheet.end, start=timesheet.start, status='rejected'
                )
                attachments = timesheet.first().attachments.filter(is_active=True)
            else:
                attachments = timesheet.attachments.filter(is_active=True)

            data = list()
            for attachment in attachments:
                response, error = get_s3_object(attachment.attachment_file.name)
                if error:
                    return Response({"message": "Unable to fetch attachments", "error": response}, status=400)
                extension = attachment.attachment_file.name.split(".")[-1]
                data.append({
                    "id": attachment.id,
                    "file_path": response,
                    "extension": extension,
                    "created": attachment.created,
                    "file_name": attachment.filename,
                })

            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['POST'], detail=True, url_path='request')
    def request_timesheet(self, request, pk):
        try:
            project = get_object_or_404(Project, id=pk)
            start = request.data['start_date']
            end = request.data['end_date']

            available_timesheet = TimeSheet.objects.filter(project=project, end__gte=start).order_by('-created')
            if available_timesheet:
                timesheet = available_timesheet.first()
                available_week = f"{timesheet.start} - {timesheet.end}"
                return Response({"error": f"Timesheet available for week {available_week}"}, status=400)

            pending_request = TimesheetRequest.objects.filter(
                project=project, start=start).exclude(status='reject').order_by('-created')
            if pending_request:
                return Response({"error": f"Timesheet already requested for week {start} - {end}"}, status=400)

            requested_week = TimesheetRequest.objects.create(
                start=start, end=end, project=project, status='request',
                consultant_comment=request.data.get('description')
            )
            content_type = ContentType.objects.get(model='timesheetrequest')
            if request.FILES.get('file', None):
                Attachment.objects.create(
                    creator_id=1,
                    object_id=requested_week.id,
                    content_type=content_type,
                    attachment_type='timesheet',
                    attachment_file=request.FILES.get('file'),
                )

            user_list = User.objects.filter(Q(role__name='finance'))
            title = f"{request.user.name} requested timesheet for the week end {str(requested_week.end)}"
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "request",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'request',
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)

            return Response({"message": "TimeSheet request sent"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


# Route - /consultant_leave/
class ConsultantLeaveViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin):
    queryset = ConsultantLeave.objects.all()
    serializer_class = ConsultantLeaveSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=True, url_path='balance')
    def balance(self, request, pk):
        try:
            # year = date.today().year
            leaves = ConsultantLeave.objects.filter(consultant_id=pk, is_expired=False, on_hold=False)
            # leaves = ConsultantLeave.objects.filter(consultant_id=pk)
            serial = ConsultantLeaveSerializer(leaves, many=True)
            return Response({"result": serial.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['POST'], detail=True, url_path='apply')
    def apply(self, request, pk, *args, **kwargs):
        try:
            attachment = None
            data = request.data
            consultant = request.user
            leave_type = get_object_or_404(ConsultantLeave, id=data.get('leave_type'), is_expired=False, on_hold=False)
            # leave_type = get_object_or_404(ConsultantLeave, id=data.get('leave_type'))
            leave = Leave.objects.create(
                leave_type=leave_type,
                consultant=consultant,
                applied_on=date.today(),
                to_date=data.get('to_date'),
                from_date=data.get('from_date'),
                description=data.get('description', None)
            )

            if data['duration_type'] == 'hourly':
                leave.total_hours = float(data.get("hours"))
            elif data['duration_type'] == 'half':
                leave.total_hours = 4
            elif data['duration_type'] == 'full':
                leave.total_hours = 8
            else:
                end = datetime.strptime(leave.to_date, "%Y-%m-%d").date()
                start = datetime.strptime(leave.from_date, "%Y-%m-%d").date()
                total_days = check_days(start, end, request)
                leave.total_hours = total_days * 8

            leave.status = 'applied' if not consultant.approval_required else 'pending'
            leave.save()
            leave_type.balance = leave_type.balance - leave.total_hours
            leave_type.save()

            content_type = ContentType.objects.get(model='leave')
            if request.FILES.get('attachment', None):
                attachment = Attachment.objects.create(
                    creator_id=1,
                    object_id=leave.id,
                    content_type=content_type,
                    attachment_type='consultant_leave',
                    attachment_file=request.FILES.get('attachment'),
                )

            if consultant.approval_required:
                path = []
                if attachment:
                    try:
                        response, error = download_s3_object(attachment.attachment_file.name)
                        path.append(response)
                    except Exception as error:
                        write_exception(error, request)

                project_obj = consultant.projects.filter(statuses__status='joined', statuses__is_current=True).order_by('-id')
                if not project_obj.first():
                    project_obj = consultant.projects.filter(statuses__status='joined').order_by('-id')
                mail_data = {
                    "template": "../templates/leave_request.html", "attachments": path,
                    "subject": f"Leave Requested from {consultant.name}",
                    "to": ["siddharth.g@consultadd.com"], "cc": ["finance@consultadd.com"], "bcc": [],
                    "context": {
                        "end_date": leave.to_date, "start_date": leave.from_date,
                        "consultant_name": consultant.name, "hours": leave.total_hours,
                        "url": f"{config.APP_URL}#/finance/leave_details/{consultant.id}"
                    }
                }
                cal_id, res, _ = send_email(mail_data, consultant.email, request)
                if not res:
                    write_exception(cal_id, request)
            return Response({"message": "leave applied successfully"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk'))
            # leaves = Leave.objects.filter(leave_type__consultant=consultant, leave_type__is_expired=False)
            leaves = Leave.objects.filter(leave_type__consultant=consultant)
            serial = LeaveSerializer(leaves, many=True)
            return Response({"result": serial.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='type')
    def type(self, request, pk):
        try:
            data = []
            leaves = ConsultantLeave.objects.filter(consultant_id=pk, is_expired=False, on_hold=False)
            for leave in leaves:
                data.append({"id": leave.id, "leave_type": leave.leave_type.display_name, "balance": leave.balance})

            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=False, url_path='holiday')
    def holiday(self, request):
        try:
            year = date.today().year
            holidays = [f"01/02/{year}", f"01/16/{year}", f"02/20/{year}", f"05/29/{year}", f"06/19/{year}",
                        f"07/04/{year}", f"09/04/{year}", f"10/09/{year}", f"11/13/{year}",
                        f"11/23/{year}", f"11/24/{year}", f"12/25/{year}"]
            return Response({"result": holidays}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


class TimetrackEventMobileViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin):
    queryset = TimetrackEvent.objects.all()
    serializer_class = TimetrackEventSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            mark_in_active()
            event_data = []
            events = TimetrackEvent.objects.filter(
                consultants=request.user, is_active=True, start__lte=date.today(), end__gte=date.today()
            )
            for event in events:
                if not TimetrackEventFeedback.objects.filter(consultant=request.user, event=event).first():
                    data = {
                        "action_link": event.action_link, "event_type": event.get_feedback_type_display(),
                        "id": event.id, "start": event.start, "is_active": event.is_active, "end": event.end,
                        "consultant_id": request.user.id, "title": event.title, "description": event.description,
                        "image": f'https://{os.environ.get("AWS_STORAGE_BUCKET_NAME")}.s3.ap-south-1.amazonaws.com/media/{event.image.name}'
                    }
                    event_data.append(data)
            return Response({'result': event_data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='feedback')
    def feedback(self, request, **kwargs):
        try:
            event = get_object_or_404(TimetrackEvent, id=kwargs.get("pk"))
            TimetrackEventFeedback.objects.create(
                feedback=request.data.get("feedback", None),
                consultant=request.user,
                event=event
            )
            return Response({"message": "Event Feedback Submitted"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)
