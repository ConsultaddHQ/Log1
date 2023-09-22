import csv
import json
from datetime import datetime, date, timedelta

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import F, Q, Subquery, OuterRef
from consultant.utils import create_and_send_notification
from django.contrib.contenttypes.models import ContentType

from rest_framework.mixins import *
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet

from constance import config
from activity.views import create_activity
from notification.models import Notification, FCMDevice
from consultant.models import Consultant
from utils_app.thred_mail import send_email as send_email_

from notification.utils import push_notification_consultant
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from project.models import  Project, TimeSheet, ConsultantLeave, Leave, TimesheetRequest
from project.utils import  create_notification_and_send_push
from project.serializers import  FinanceSerializer,ConsultantTimeSheetSerializer, LeaveSerializer, ConsultantLeaveSerializer,TimesheetRequestSerializer


# Route - /finance_payStubs
class FinancePayStubsViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = FinanceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query')
            start = request.GET.get('start')
            paystubs_status = request.GET.get('status', 'approved')
            end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))

            paystubs = TimeSheet.objects.filter(project=kwargs.get('pk')).order_by('-created')

            if query:
                query = query.replace(':amp:', '&')
                paystubs = paystubs.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if start:
                paystubs = paystubs.filter(start__gte=start)

            if paystubs_status == 'pending_for_approval':
                paystubs = paystubs.filter(status__in=['submitted', 'updated'], is_active=True)
            elif paystubs_status == 'approved':
                paystubs = paystubs.exclude(status='draft')

            total = paystubs.count()
            serializer = self.serializer_class(paystubs[first:last], many=True)
            return Response({"data": serializer.data, 'total': total}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query')
            end_date = request.GET.get('end')
            start_date = request.GET.get('start')
            timesheet_status = request.GET.get('timesheet_status')

            project_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue', 'complete',
                'joined', 'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]
            project_qs = Project.objects.filter(
                statuses__status__in=project_status, statuses__is_current=True,
                submission__work_type_in=['w2','full_time'], timesheets__isnull=False
            ).order_by('id').distinct('id')

            if query:
                query = query.replace(':amp:', '&')
                project_qs = project_qs.filter(
                    Q(consultant__name__istartswith=query) |
                    Q(employer__startswith=query) |
                    Q(submission__client__icontains=query) |
                    Q(submission__lead__vendor_company__name__icontains=query)
                ).order_by('id').distinct('id')

            if start_date:
                project_qs = project_qs.filter(timesheets__start__gte=start_date)
            if end_date:
                project_qs = project_qs.filter(timesheets__end__lte=end_date)
            if timesheet_status == 'pending_for_approval':
                project_qs = project_qs.filter(timesheets__status__in=['submitted', 'updated'])
            elif timesheet_status:
                project_qs = project_qs.filter(timsheets__status=timesheet_status, is_active=True)

            pending_timesheet_count = project_qs.filter(timesheets__status__in=["updated", "submitted"]).count()

            project_list = [
                {
                    "id": obj.consultant.id,
                    "name": obj.consultant.name,
                    "email": obj.consultant.email,
                    "approval_required": obj.consultant.approval_required,
                    "timesheet_status": (
                        obj.timesheets.latest().status if obj.timesheets.exists() else obj.timesheets.latest().status
                    ) if obj.timesheets.exists() else None,
                    "project": {
                        'id': obj.id,
                        'team': obj.employer,
                        'start_date': obj.start_date,
                        'client': obj.submission.client,
                        'vendor': obj.submission.lead.vendor_company.name,
                        'project_type': obj.submission.get_work_type_display(),
                        'status': obj.status
                    }
                }
                for obj in project_qs[first: last]
            ]

            data = {
                "pending_timesheet": pending_timesheet_count,
                "project_list": project_list,
                "total": len(project_list)
            }
            return Response({"data": data}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            if 'finance' in request.user.roles:
                paystubs_id = kwargs.get('pk')
                paystubs = get_object_or_404(TimeSheet, id=paystubs_id)
                paystubs.remark = request.data.get('remark', None)
                paystubs.status = request.data.get('status')
                paystubs.status_updated_at = timezone.now()
                paystubs.status_updated_by = request.user
                paystubs.save()
                notification_type = "rejected" if request.data.get('status') == 'rejected' else "Approved"
                create_notification_and_send_push(paystubs, request, notification_type)
                serializer = self.serializer_class(paystubs)
                return Response({"data": serializer.data, "message": "PayStubs is updated"}, status=status.HTTP_202_ACCEPTED)
            return Response({"message": "You don't have access"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Route - /finance_timesheet
class FinanceTimeSheetViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = FinanceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        start = request.GET.get('start', None)
        end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))
        timesheet_status = request.GET.get('status', None)

        try:
            project_id = kwargs.get('pk', None)
            timesheet_qs = TimeSheet.objects.filter(project=project_id).order_by('-created')

            if query:
                query = query.lstrip().replace(':amp:', '&')
                timesheet_qs = timesheet_qs.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if start:
                if not end:
                    end = date.today().strftime('%Y-%m-%d')
                timesheet_qs = timesheet_qs.filter(start__gte=start, end__lte=end)

            if timesheet_status:
                if timesheet_status == 'pending_for_approval':
                    timesheet_qs = timesheet_qs.filter(status__in=['submitted', 'updated'], is_active=True)
                else:
                    timesheet_qs = timesheet_qs.filter(status=timesheet_status, is_active=True)
            else:
                timesheet_qs = timesheet_qs.exclude(status='draft')

            total = timesheet_qs.count()
            serializer = self.serializer_class(timesheet_qs[first:last], many=True)
            return Response({"data": serializer.data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        end_date = request.GET.get('end', None)
        start_date = request.GET.get('start', None)
        timesheet_status = request.GET.get('timesheet_status', None)
        project_status = request.GET.get('project_status', None)

        try:
            terminated_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue',
                'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            project_qs = Project.objects.filter(
                submission__work_type="c2c", timesheets__isnull=False
            ).order_by('id').distinct('id')

            if project_status:
                if project_status == 'active':
                    project_qs = project_qs.filter(
                        statuses__status='joined', statuses__is_current=True
                    )
                elif project_status == 'complete':
                    project_qs = project_qs.filter(
                        statuses__status='complete', statuses__is_current=True
                    )
                else:
                     project_qs = project_qs.filter(
                        statuses__status_in=terminated_status, statuses__is_current=True
                    )
            else:
                project_qs = project_qs.filter(
                    statuses__status_in=Q(statuses__status__in=terminated_status) |
                                        Q(statuses__status__in=['joined', 'complete']))

            if query:
                query = query.lstrip().replace(':amp:', '&')
                project_qs = project_qs.filter(
                    Q(consultant__name__istartswith=query) |
                    Q(employer__startswith=query) |
                    Q(submission__client__icontains=query) |
                    Q(submission__lead__vendor_company__name__icontains=query)
                ).order_by('id').distinct('id')

            if start_date:
                project_qs = project_qs.filter(timesheets__start__gte=start_date)
            if end_date:
                project_qs = project_qs.filter(timesheets__end__lte=end_date)
            if timesheet_status == 'pending':
                project_qs = project_qs.filter(timesheets__status__in=['submitted', 'updated'])
            elif timesheet_status:
                project_qs = project_qs.filter(timesheets__status=timesheet_status)

            pending_timesheet_count = project_qs.filter(timesheets__status__in=["updated", "submitted"]).count()

            project_ls = []
            for obj in project_qs[first:last]:
                consultant = obj.consultant
                ts_obj = TimeSheet.objects.filter(project=obj, status__in=["updated", "submitted"])
                try:
                    ts_status = ts_obj.latest().status if ts_obj else TimeSheet.objects.filter(
                        project=obj).latest().status
                except:
                    ts_status = None

                project = {
                    "id": consultant.id,
                    "name": consultant.name,
                    "email": consultant.email,
                    "approval_required": consultant.approval_required,
                    "timesheet_status": ts_status,
                    "project": {
                        'id': obj.id,
                        'team': obj.employer,
                        'start_date': obj.start_date,
                        'client': obj.submission.client,
                        'vendor': obj.submission.lead.vendor_company.name,
                        'project_type': obj.submission.get_work_type_display(),
                        'status': "terminate" if obj.status.startswith('terminated') else obj.status
                    }
                }
                project_ls.append(project)

            data = {
                "pending_timesheet": pending_timesheet_count,
                "project_list": project_ls,
                "total": len(project_ls)
            }
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            if 'finance' in request.user.roles:
                timesheet_id = kwargs.get('pk')
                timesheet = get_object_or_404(TimeSheet, id=timesheet_id)
                timesheet.remark = request.data.get('remark', None)
                timesheet.status = request.data.get('status')
                timesheet.status_updated_at = datetime.now()
                timesheet.status_updated_by = request.user
                timesheet.save()
                if request.data.get('status') == 'rejected':
                    create_notification_and_send_push(timesheet, request, "rejected")
                    serializer = self.serializer_class(timesheet)
                else:
                    create_notification_and_send_push(timesheet, request, "Approved")
                    serializer = self.serializer_class(timesheet)
                return Response({"data": serializer.data, "message": "Timesheet is updated"},
                                status=status.HTTP_202_ACCEPTED)
            return Response({"message": "You don't have access"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=["post"], detail=False, url_name="send_reminder")
    def send_reminder(self, request, *args, **kwargs):
        try:
            consultant_ids = request.data.get('consultant_ids', [])
            start = request.data.get('start', None)
            end = request.data.get('end', None)
            if not consultant_ids:
                return Response({"message": "mail sent"}, status=400)
            for consultant_id in consultant_ids:
                consultant = Consultant.objects.get(id=consultant_id)
                timesheet_list = TimeSheet.objects.filter(
                    status='draft', project__consultant__id=consultant_id, is_active=True
                )

                if start is not None:
                    timesheet_list = timesheet_list.filter(start__gte=start)

                if end is not None:
                    timesheet_list = timesheet_list.filter(end__lte=end)
                mail_data = {
                    'cc': [config.FINANCE, 'yash.j@consultadd.com'],
                    'bcc': [],
                    'template': '../templates/reminder.html',
                    'to': [consultant.email],
                    'subject': "Timesheet reminder",
                    'context': {
                        'consultant': consultant.name,
                        'timesheet_list': timesheet_list
                    }
                }
                send_email_(mail_data, 'sakshi.shetty@consultadd.com', request=request)
            return Response({"message": "mail sent"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    @action(methods=["get"], detail=True, url_name="from_notification")
    def from_notification(self, request, pk):
        try:
            queryset = TimeSheet.objects.filter(id=pk)
            serializer = self.serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=["get"], detail=True, url_name="projects")
    def projects(self, request, *args, **kwargs):
        try:
            project_id = request.GET.get('project_id', None)
            work_type = request.GET.get('project_type', None)
            if not project_id:
                projects = Project.objects.filter(submission__work_type=work_type) \
                    if work_type else Project.objects.all()
                projects = projects.filter(
                    Q(consultant_id=kwargs.get('pk'), statuses__is_current=True) & (
                            Q(statuses__status='joined') |
                            Q(statuses__status__istartswith='terminated') |
                            Q(statuses__status__in=['complete', 'extended'])
                    )
                ).annotate(
                    client=F('submission__client'),
                    work_type=F('submission__work_type'),
                    vendor=F('submission__lead__vendor_company__name'),
                ).values('id', 'client', 'vendor', 'work_type').order_by('-start_date')
                return Response({'result': projects}, status=200)

            else:
                project = get_object_or_404(Project, id=project_id, consultant_id=kwargs.get('pk'))
                data = {
                    "id": project.consultant.id, "project_id": project.id,
                    "vendor": project.submission.lead.vendor_company.name,
                    "work_type": project.submission.get_work_type_display(),
                    "name": project.consultant.name, "email": project.consultant.email,
                    "team": project.submission.marketing_team.name, "start_date": project.start_date,
                    "client": project.submission.client, "marketer": project.submission.created_by.employee_name
                }
                return Response({'result': data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    @action(methods=["GET", "PUT"], detail=False, url_name="request_timesheet")
    def request_timesheet(self, request, *args, **kwargs):
        try:
            if request.method == 'GET':
                end = request.GET.get('end', None)
                start = request.GET.get('start', None)
                query = request.GET.get('query', None)
                consultant_id = request.GET.get('consultant_id')
                requested_timesheets = TimesheetRequest.objects.filter(project__consultant_id=consultant_id)
                if query:
                    requested_timesheets = requested_timesheets.filter(
                        Q(project__submission__client__istartswith=query) |
                        Q(project__submission__lead__vendor_company__name__istartswith=query)
                    )
                if start and end:
                    requested_timesheets = requested_timesheets.filter(start__gte=start, end__lte=end)
                serializer = TimesheetRequestSerializer(requested_timesheets, many=True)
                return Response({"data": serializer.data}, status=200)

            elif request.method == 'PUT':
                request_id = request.data['request_id']
                timesheet = get_object_or_404(TimesheetRequest, id=request_id)

                available_timesheet = TimeSheet.objects.filter(project=timesheet.project, end__gte=timesheet.start
                                                               ).order_by('-created')
                if available_timesheet:
                    timesheet.status = 'reject'
                    timesheet.save()
                    timesheet = available_timesheet.first()
                    available_week = f"{timesheet.start} - {timesheet.end}"
                    return Response({"error": f"Timesheet available for week {available_week}"}, status=400)

                timesheet.reviewed_by = request.user
                timesheet.status = request.data.get('status', timesheet.status)
                timesheet.reviewer_comment = request.data.get('reviewer_comment')
                timesheet.save()

                if timesheet.status == "accepted":
                    new_ts, created = TimeSheet.objects.get_or_create(
                        project=timesheet.project, start=timesheet.start, end=timesheet.end
                    )
                    if created:
                        new_ts.hours = 0
                        new_ts.save()

                title = f"{request.user.employee_name} {timesheet.status} the timesheet request for week " \
                        f"{str(timesheet.start)} - {str(timesheet.end)}"

                message_body = {
                    "body": title, "title": title, "category": "rejected",
                    "show_in_foreground": True, "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "data": {
                        'target': 'timesheet', 'target_id': timesheet.id,
                        'is_read': False, 'is_deleted': False, 'timestamp': str(timezone.now()),
                    },
                }
                object_ids = timesheet.project.consultant.consultant_token.all().values_list('key', flat=True)
                registration_ids = list(
                    FCMDevice.objects.filter(
                        object_id__in=list(object_ids), content_type__model='consultanttoken'
                    ).values_list('device_id', flat=True))
                push_notification_consultant(registration_ids, message_body)

                return Response({"message": f"TimeSheet request {timesheet.get_status_display()}"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    @action(methods=["put"], detail=False, url_name="approval_required")
    def approval_required(self, request, *args, **kwargs):
        try:
            # updated_consultants = ''
            approval = request.data.get('action', True)
            consultant_ids = request.data.get('consultant_ids', [])

            for consultant_id in consultant_ids:
                consultant = Consultant.objects.get(id=consultant_id)
                if consultant.approval_required == approval:
                    continue
                consultant.approval_required = approval
                consultant.save()

                # updated_consultants = updated_consultants + consultant.name + ' '
                required = '' if approval else 'not '
                desc = f"{request.user.employee_name} marked {consultant.name} approval as {required}required"
                create_activity(consultant.id, 'leave', request.user, desc, 'updated')

            return Response({"message": "Consultant Approval Updated"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

# Route - /finance_leave
class FinanceLeaveViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        try:
            project_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue', 'complete',
                'joined', 'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            consultant_ids = Project.objects.filter(
                statuses__status__in=project_status, statuses__is_current=True
            ).values_list('consultant', flat=True)

            consultants = Consultant.objects.filter(
                id__in=list(consultant_ids),
                leaves__isnull=False,
                projects__submission__status__in=['draft', 'sub', 'project', 'in_offer', 'interview']
            ).order_by('id').distinct('id')

            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = Consultant.objects.filter(
                    Q(name__istartswith=query) |
                    Q(projects__employer__startswith=query) |
                    Q(projects__submission__client__icontains=query) |
                    Q(projects__submission__lead__vendor_company__name__icontains=query)
                ).order_by('id').distinct('id')

            queryset = consultants.order_by('name').distinct('name')
            total = queryset.count()
            serializer = ConsultantTimeSheetSerializer(queryset[first:last], many=True)
            return Response({"data": serializer.data, 'total': total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            end = request.GET.get('end')
            start = request.GET.get('start')
            status = request.GET.get('status')
            leave_type = request.GET.get('leave_type')
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk', None))
            queryset = self.queryset.filter(consultant=consultant).order_by('-created')
            if status == 'applied':
                queryset = queryset.filter(status__in=['pending', 'applied'])
            if end:
                queryset = queryset.filter(to_date__lte=end)
            if start:
                queryset = queryset.filter(from_date__gte=start)
            if leave_type:
                queryset = queryset.filter(leave_type__leave_type__id=leave_type)

            serializer = LeaveSerializer(queryset, many=True)
            return Response({"data": serializer.data[first: last], 'total': len(queryset)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        consultant = get_object_or_404(Consultant, id=kwargs.get('consultant_id'))

        try:
            leave_status = request.data.get('status', None)
            if not leave_status:
                return Response({"message": "No action selected"}, status=200)
            leave = get_object_or_404(Leave, id=kwargs.get('pk'), consultant=consultant)
            prev_status = leave.get_status_display()
            leave.remarks = request.data.get('remarks', None)
            leave.save()

            consultant_leave = leave.leave_type
            if not leave_status or leave_status == leave.status:
                return Response({"message": "Status Not Updated"}, status=200)

            if leave_status.upper() == "REJECTED":
                leave_status = "rejected_1st_level" if leave.status == 'pending' else "rejected"
                consultant_leave.balance += leave.total_hours
                consultant_leave.save()

            elif leave_status.upper() == "APPROVED":
                if "rejected" in leave.status:
                    consultant_leave.balance -= leave.total_hours
                    consultant_leave.save()
                    leave_status = "approved" if leave.status == 'rejected' else "applied"
                else:
                    if leave.status == 'pending':
                        leave_status = "applied"
                    elif leave.status == 'applied':
                        leave_status = "approved"

            leave.status = leave_status
            leave.save()
            sender_content_type = ContentType.objects.get(model='user')
            target_content_type = ContentType.objects.get(model='leave')
            recipient_content_type = ContentType.objects.get(model='consultant')

            if prev_status == 'pending' and request.data['status'] == 'approved':
                title = f"Leave initial level approval granted from {request.user.employee_name}"
            else:
                title = f"Leave {leave.status} for date {leave.from_date}"

            Notification.objects.create(
                category="info", recipient_content_type=recipient_content_type,
                title=title, recipient_object_id=leave.consultant.id,
                sender_content_type=sender_content_type, target_content_type=target_content_type,
                description=title, target_object_id=leave.id, sender_object_id=request.user.id,
            )

            # Push Notification
            message_body = {
                "body": title, "title": title, "category": "info",
                "show_in_foreground": True, "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "data": {
                    'target': 'timesheet', 'target_id': leave.id,
                    'is_read': False, 'is_deleted': False, 'timestamp': str(timezone.now()),
                },
            }
            object_ids = leave.consultant.consultant_token.all().values_list('key', flat=True)
            registration_ids = list(
                FCMDevice.objects.filter(
                    object_id__in=list(object_ids), content_type__model='consultanttoken'
                ).values_list('device_id', flat=True))
            push_notification_consultant(registration_ids, message_body)

            return Response({"message": "Leave updated successfully"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=["get"], detail=False, url_name="balances")
    def balances(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('consultant_id')
            year = request.GET.get('year', date.today().year)
            queryset = ConsultantLeave.objects.filter(consultant_id=consultant_id, year=year)
            # queryset = ConsultantLeave.objects.filter(consultant_id=consultant_id)
            serializer = ConsultantLeaveSerializer(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=["put"], detail=True, url_name="update_balances")
    def update_balances(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('consultant_id')
            leave_type = get_object_or_404(ConsultantLeave, id=kwargs.get('pk'))
            updated_balance = request.data.get('granted_leaves')
            if updated_balance > leave_type.granted:
                diff = updated_balance - leave_type.granted
                leave_type.granted += diff
                leave_type.save()
            leave_type.balance = updated_balance
            leave_type.save()

            sender_content_type = ContentType.objects.get(model='user')
            target_content_type = ContentType.objects.get(model='leave')
            recipient_content_type = ContentType.objects.get(model='consultant')
            title = f"{leave_type.leave_type.display_name} balance updated"

            Notification.objects.create(
                title=title, recipient_object_id=consultant_id,
                category="info", recipient_content_type=recipient_content_type,
                sender_content_type=sender_content_type, target_content_type=target_content_type,
                description=title, target_object_id=leave_type.id, sender_object_id=request.user.id,
            )

            # Push Notification
            message_body = {
                "body": title, "title": title, "category": "info",
                "show_in_foreground": True, "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "data": {
                    'target': 'timesheet', 'target_id': leave_type.id,
                    'is_read': False, 'is_deleted': False, 'timestamp': str(timezone.now()),
                },
            }
            object_ids = leave_type.consultant.consultant_token.all().values_list('key', flat=True)
            registration_ids = list(
                FCMDevice.objects.filter(
                    object_id__in=list(object_ids), content_type__model='consultanttoken'
                ).values_list('device_id', flat=True))
            push_notification_consultant(registration_ids, message_body)

            return Response({"message": "Leave balance updated"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)