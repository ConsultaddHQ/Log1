import csv
import json
from datetime import datetime, date, timedelta

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import F, Q, Count
from django.db.models import Case, When, Value, CharField
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
# from finance.models import TimetrackEvent, Leave, TimeSheet, TimesheetRequest, ConsultantLeave
from finance.serializers import FinanceDetailSerializer, FinanceSerializer, TimetrackEventSerializer, LeaveSerializer, \
    TimesheetRequestSerializer
from notification.models import Notification, FCMDevice
from consultant.models import Consultant, ConsultantRateRevision, ConsultantPOC
from utils_app.thred_mail import send_email as send_email_

from notification.utils import push_notification_consultant
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from project.models import Project, TimetrackEvent, Leave, TimeSheet, TimesheetRequest, ConsultantLeave
from project.utils import create_notification_and_send_push, mark_in_active
from project.serializers import ConsultantLeaveSerializer
from utils_app.utils import export_to_csv


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
            paystub_status = request.GET.get('status', 'approved')
            end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))

            paystub_qs = TimeSheet.objects.filter(project=kwargs.get('pk')).order_by('-created')

            if query:
                query = query.replace(':amp:', '&')
                paystub_qs = paystub_qs.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if start:
                if not end:
                    end = date.today().strftime('%Y-%m-%d')
                paystub_qs = paystub_qs.filter(start__gte=start, end__lte=end)

            if paystub_status:
                if paystub_status == 'pending':
                    paystub_qs = paystub_qs.filter(status__in=['submitted', 'updated'], is_active=True)
                else:
                    paystub_qs = paystub_qs.filter(status=paystub_status, is_active=True)
            else:
                paystub_qs = paystub_qs.exclude(status='draft')

            total = paystub_qs.count()
            serializer = FinanceDetailSerializer(paystub_qs[first:last], many=True)
            return Response({"data": serializer.data, 'total': total}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            query = request.GET.get('query', '')
            end_date = request.GET.get('end', '')
            vendor = request.GET.get('vendor', '')
            client = request.GET.get('client', '')
            start_date = request.GET.get('start', '')
            project_status = request.GET.get('project_status', '')
            paystub_status = request.GET.get('paystub_status', '')

            terminated_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue',
                'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            project_qs = Project.objects.filter(
                submission__work_type__in=['w2','full_time'], timesheets__isnull=False
            ).order_by('id').distinct('id')

            if client:
                project_qs = project_qs.filter(submission__istartswith=client)

            if vendor:
                project_qs = project_qs.filter(submission__lead__vendor_company__name__istartsswith=vendor)

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
                        statuses__status__in=terminated_status, statuses__is_current=True
                    )
            else:
                project_qs = project_qs.filter(
                    statuses__status__in=terminated_status + ['joined', 'complete']
                )

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

            if paystub_status == 'pending':
                project_qs = project_qs.filter(timesheets__status__in=['submitted', 'updated'])
            elif paystub_status:
                project_qs = project_qs.filter(timesheets__status=paystub_status)

            project_serializer = FinanceSerializer(project_qs[first:last], many=True)

            data = {
                "pending_timesheet": project_qs.filter(timesheets__status__in=["updated", "submitted"]).count(),
                "project_list": project_serializer.data,
                "total": project_qs.count(),
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
class FinanceTimeSheetViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = FinanceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        start = request.GET.get('start', None)
        end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))
        timesheet_status = request.GET.get('status', None)

        try:
            project_id = kwargs.get('pk', None)
            timesheet_qs = TimeSheet.objects.filter(project=project_id).order_by('-created')

            if start:
                if not end:
                    end = date.today().strftime('%Y-%m-%d')
                timesheet_qs = timesheet_qs.filter(start__gte=start, end__lte=end)

            if timesheet_status:
                if timesheet_status == 'pending':
                    timesheet_qs = timesheet_qs.filter(status__in=['submitted', 'updated'], is_active=True)
                else:
                    timesheet_qs = timesheet_qs.filter(status=timesheet_status, is_active=True)
            else:
                timesheet_qs = timesheet_qs.exclude(status='draft')

            custom_order = Case(
                When(status='updated', then=Value(1)),
                When(status='pending', then=Value(2)),
                When(status='rejected', then=Value(3)),
                When(status='approved', then=Value(4)),
                When(status='draft', then=Value(5)),
                default=Value(6),
                output_field=CharField()
            )

            # Order the queryset based on custom_order and created date
            timesheet_qs = timesheet_qs.annotate(custom_order=custom_order).order_by('custom_order', '-created')

            total = timesheet_qs.count()
            serializer = FinanceDetailSerializer(timesheet_qs[first:last], many=True)

            project = Project.objects.get(id=project_id);

            data = {
                "project":{
                    'id': project.id,
                    'employer': project.employer,
                    'status': "terminated" if project.statuses.filter(status__istartswith='terminated') else project.status,
                    'start_date': project.start_date,
                    'submission': {
                        'client': project.submission.client,
                        'vendor': project.submission.lead.vendor_company.name,
                        'work_type': project.submission.get_work_type_display(),
                    },
                "timesheets":serializer.data
                },
            }

            return Response({"data": data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            query = request.GET.get('query', '')
            end_date = request.GET.get('end', '')
            vendor = request.GET.get('vendor', '')
            client = request.GET.get('client', '')
            start_date = request.GET.get('start', '')
            project_status = request.GET.get('project_status', '')
            timesheet_status = request.GET.get('timesheet_status', '')

            terminated_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue',
                'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            project_qs = Project.objects.filter(
                submission__work_type="c2c", timesheets__isnull=False
            ).order_by('id').distinct('id')

            if client:
                project_qs = project_qs.filter(submission__istartswith=client)

            if vendor:
                project_qs = project_qs.filter(submission__lead__vendor_company__name__istartsswith=vendor)

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
                        statuses__status__in=terminated_status, statuses__is_current=True
                    )
            else:
                project_qs = project_qs.filter(
                    statuses__status__in=terminated_status + ['joined', 'complete']
                )

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

            project_serializer = FinanceSerializer(project_qs[first:last], many=True)

            data = {
                "pending_timesheet": project_qs.filter(timesheets__status__in=["updated", "submitted"]).count(),
                "project_list": project_serializer.data,
                "total": project_qs.count(),
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
                    serializer = FinanceDetailSerializer(timesheet)
                else:
                    create_notification_and_send_push(timesheet, request, "Approved")
                    serializer = FinanceDetailSerializer(timesheet)
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
            serializer = FinanceDetailSerializer(queryset, many=True)
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
        start_date = request.GET.get('start', None)
        end_date = request.GET.get('start', None)
        leave_status = request.GET.get('leave_status', None)
        leave_type = request.GET.get('leave_type', None)
        approval_required = request.GET.get('approval_required', 'false')

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

            consultants = Consultant.objects.filter(id__in=list(consultant_ids),).order_by('id').distinct('id')

            if leave_status:
                consultants=consultants.filter(leaves__status=leave_status)

            if leave_type:
                consultants = consultants.filter(leaves__leave_type__leave_type=leave_type)

            if approval_required == 'true':
                consultants = consultants.filter(approval_required=True)

            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = Consultant.objects.filter(
                    Q(name__istartswith=query) |
                    Q(projects__employer__startswith=query) |
                    Q(projects__submission__client__icontains=query) |
                    Q(projects__submission__lead__vendor_company__name__icontains=query)
                ).order_by('id').distinct('id')

            if start_date:
                consultants.filter(leaves__from_date__gte=start_date)
            if end_date:
                consultants = consultants.filter(leaves__to_date__lte=end_date)

            consultant_list=[]

            for consultant in consultants:
                consultant = {
                    "id":consultant.id,
                    "name":consultant.name,
                    "email":consultant.email,
                    "employer":"Boto3",
                    "leave_status":consultant.leaves.latest().leave_type.leave_type.name if consultant.leaves.count() != 0 else "Not applied yet"
                }
                consultant_list.append(consultant)

            data = {
                "total_pending":0,
                "pending_level_1":0,
                "pending_level_2":0,
                "consultants":consultant_list
            }

            total = consultants.count()
            # serializer = ConsultantTimeSheetSerializer(consultants[first:last], many=True)
            return Response({"data": data, 'total': total}, status=200)
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


class TimetrackEventViewSet(GenericViewSet, CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
                            DestroyModelMixin):
    queryset = TimetrackEvent.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_classes = TimetrackEventSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            mark_in_active()
            filter_for = request.GET.get('filter_for', 'all')
            if filter_for == 'my':
                queryset = TimetrackEvent.objects.filter(created_by=request.user)
            else:
                queryset = TimetrackEvent.objects.all()
            serializer = TimetrackEventSerializer(queryset, many=True)
            return Response({'result': serializer.data[first: last], "total": len(serializer.data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            event_info = get_object_or_404(TimetrackEvent, id=kwargs.get("pk"))
            serializer = TimetrackEventSerializer(event_info)
            return Response({'data': serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            end_datatime = request.data.get('end')
            start_datetime = request.data.get('start', None)

            if request.data.get('all', False):
                distinct_by = 'submission__consultant_marketing__consultant_id'
                consultants_ids = Project.objects.filter(
                    statuses__status='joined', statuses__is_current=True
                ).values_list(distinct_by, flat=True).order_by(distinct_by).distinct(distinct_by)
            else:
                consultants_ids = json.loads(request.data.get('consultants', '[]'))

            if not start_datetime or not consultants_ids:
                Response({"message": "Start Time or Consultant Ids not provided"}, status=201)

            event = TimetrackEvent.objects.create(
                start=start_datetime,
                end=end_datatime,
                created_by=request.user,
                title=request.data.get('title', None),
                image=request.FILES.get('image', None),
                feedback_type=request.data.get('feedback_type'),
                event_type=request.data.get('event_type', None),
                description=request.data.get('description', None),
                action_link=request.data.get('action_link', None),
            )
            for consultant_id in consultants_ids:
                consultant = get_object_or_404(Consultant, id=consultant_id)
                event.consultants.add(consultant)

            event.save()
            return Response({"message": "Event Created Successfully"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            event = get_object_or_404(TimetrackEvent, id=kwargs.get('pk', None))
            consultants_ids = json.loads(request.data.get('consultants', '[]'))

            if event.created_by == request.user:
                event.start = request.data.get('start')
                if request.data.get('start') and request.data.get('end'):
                    event.start = request.data.get('start')
                    event.end = request.data.get('end')
                if request.data.get('description'):
                    event.description = request.data.get('description')
                if request.data.get('title'):
                    event.title = request.data.get('title')
                if request.data.get('action_link'):
                    event.action_link = request.data.get('action_link')
                if request.data.get('feedback_type'):
                    event.feedback_type = request.data.get('feedback_type')
                if consultants_ids:
                    event.consultants.clear()
                    for id in consultants_ids:
                        consultant = get_object_or_404(Consultant, id=id)
                        event.consultants.add(consultant)
                if request.FILES.get('image', None):
                    event.image = request.FILES['image']
                event.save()
            else:
                return Response({"message": "You don't have permission to update the event"}, status=403)

            serializer = TimetrackEventSerializer(event)
            return Response({"result": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            event = get_object_or_404(TimetrackEvent, id=kwargs.get('pk', None))
            if event.created_by == request.user:
                event.delete()
                return Response({"message": "Event Removed Successfully"}, status=202)
            return Response({"message": "You don't have permission to delete the event"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    @action(methods=["get"], detail=True, url_name="event_feedback")
    def event_feedback(self, request, *args, **kwargs):
        try:
            event = get_object_or_404(TimetrackEvent, id=kwargs.get('pk'))
            consultant_feedback = event.feedback.all().values('id', 'feedback').annotate(
                consultant_name=F('consultant__name')
            )
            columns = [
                {"name": "id", "display_name": "Feedback Id"},
                {"name": "consultant_name", "display_name": "Consultant Name"},
                {"name": "feedback", "display_name": "Feedback"},
            ]
            file_url = export_to_csv(
                consultant_feedback, columns, f"event_feedback_{datetime.now().strftime('%d-%B-%Y')}.csv",
                request, "Event Feedback"
            )
            return Response({"data": file_url}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

class ConsultantRevisionViewSet(GenericViewSet, CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
                                DestroyModelMixin):
    queryset = ConsultantRateRevision.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            data = []
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            query = request.GET.get('query', None)
            margin = request.GET.get('margin', 'below_21')
            if start:
                start = datetime.strptime(start, '%Y-%m-%d').date()
            if end:
                end = datetime.strptime(end, '%Y-%m-%d').date()
            if margin == '21-30':
                gte, lte = 21, 30
            elif margin == 'above_30':
                gte, lte = 30, 100
            else:
                gte, lte = 0, 21
            export = json.loads(request.GET.get('export', 'false'))
            consultants = Consultant.objects.filter(status__in=['on_project'])
            if query:
                consultants = consultants.filter(name__istartswith=query)
            for consultant in consultants:
                last_revision = ConsultantRateRevision.objects.filter(consultant_id=consultant.id, end=None).first()
                if last_revision:
                    consultant_rate = last_revision.rate
                    revision_date = last_revision.start
                else:
                    consultant_rate = 0
                    revision_date = date(2010, 1, 1)
                project = Project.objects.filter(
                    is_remote=False, statuses__status='joined', statuses__is_current=True
                ).select_related('submission').filter(submission__consultant_marketing__consultant_id=consultant.id,
                                                      ).order_by('-rate').first()
                if not project:
                    continue
                project_rate = project.rate
                if revision_date < project.start_date:
                    revision_date = project.start_date
                if start and revision_date < start:
                    continue
                if end and revision_date > end:
                    continue
                margin = project_rate - consultant_rate
                margin_percentage = round((margin / project_rate) * 100, 2)
                marketer = {}
                assigned_marketer = ConsultantPOC.objects.filter(
                    poc_type='marketer', consultant_id=consultant.id, end=None).first()
                if not assigned_marketer:
                    marketer['name'] = project.submission.created_by.employee_name
                    marketer['email'] = project.submission.created_by.email
                else:
                    marketer['name'] = assigned_marketer.poc.employee_name
                    marketer['email'] = assigned_marketer.poc.email
                if (start or end) and gte <= margin_percentage <= lte:
                    data.append({
                        "rate": consultant_rate,
                        "po_rate": project_rate,
                        "last_revision": revision_date,
                        "consultant_id": consultant.id,
                        "margin": f"{round(margin, 1)}({margin_percentage}%)",
                        "consultant_name": consultant.name,
                        "consultant_email": consultant.email,
                        "marketer_name": marketer.get('name'),
                        "marketer_email": marketer.get('email'),
                        'vendor_name': project.submission.lead.vendor_company.name
                    })
                elif (date.today() - timedelta(days=170) > revision_date) and gte <= margin_percentage <= lte:
                    data.append({
                        "rate": consultant_rate,
                        "po_rate": project_rate,
                        "last_revision": revision_date,
                        "consultant_id": consultant.id,
                        "consultant_name": consultant.name,
                        "consultant_email": consultant.email,
                        "marketer_name": marketer.get('name'),
                        "marketer_email": marketer.get('email'),
                        "margin": f"{round(margin, 1)}({margin_percentage}%)",
                        'vendor_name': project.submission.lead.vendor_company.name
                    })
            file_url = None
            if export:
                columns = [
                    {"name": "consultant_name", "display_name": "Consultant Name"},
                    {"name": "consultant_email", "display_name": "Consultant Email"},
                    {"name": "rate", "display_name": "Consultant Rate"},
                    {"name": "po_rate", "display_name": "Project Rate"},
                    {"name": "vendor_name", "display_name": "Vendor Name"},
                    {"name": "last_revision", "display_name": "Last Revision"},
                    {"name": "margin", "display_name": "Margin"}
                ]
                file_url = export_to_csv(
                    data, columns, f"consultant_rate_revision_{datetime.now().strftime('%d-%B-%Y')}.csv",
                    None, "Consultant Rate Revision"
                )
            return Response({"data": data[first: last], "url": file_url, "total": len(data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
