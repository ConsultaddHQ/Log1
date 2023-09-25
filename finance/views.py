from datetime import datetime, date

from django.utils import timezone
from django.db.models import F, Q, Count
from django.shortcuts import get_object_or_404
from django.db.models import Case, When, Value, CharField
from django.contrib.contenttypes.models import ContentType

from rest_framework.mixins import *
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config
from consultant.models import Consultant
from activity.views import create_activity
from notification.models import Notification, FCMDevice
from utils_app.thred_mail import send_email as send_email_
from finance.serializers import FinanceDetailSerializer, FinanceSerializer, LeaveSerializer, \
    TimesheetRequestSerializer

from project.serializers import ConsultantLeaveSerializer
from notification.utils import push_notification_consultant
from project.utils import create_notification_and_send_push
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from project.models import Project, Leave, TimeSheet, TimesheetRequest, ConsultantLeave


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
            paystub_status = request.GET.get('status', [])
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
                if 'pending' in paystub_status:
                    paystub_status.remove('pending')
                    paystub_status.apppned(['submitted', 'updated'])
                paystub_qs = paystub_qs.filter(
                    statuses__status__in=paystub_status)

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
            paystub_qs = paystub_qs.annotate(custom_order=custom_order).order_by('custom_order', '-created')
            total = paystub_qs.count()
            project = get_object_or_404(Project,id=kwargs.get('pk'))
            submission = project.submission
            data = {
            'id': project.id,
            'status':project.status,
            'employer': project.employer,
            'start_date': project.start_date,
            'frequency':project.timesheet_frequency,
            'consultant_name':project.consultant.name,
            'submission' : {
                'client': submission.client,
                'vendor': submission.lead.vendor_company.name,
                'work_type': submission.get_work_type_display(),
            },
            "paystub_ls":FinanceDetailSerializer(paystub_qs[first:last], many=True).data
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
            project_status = request.GET.get('project_status', [])
            paystub_status = request.GET.get('paystub_status', [])

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
                if 'terminated' in project_status:
                    project_status.apppned(terminated_status)
                project_qs = project_qs.filter(
                    statuses__status__in=terminated_status + ['joined', 'complete'])

            if paystub_status:
                if 'pending' in paystub_status:
                    paystub_status.remove('pending')
                    paystub_status.apppned(['submitted', 'updated'])
                project_qs = project_qs.filter(
                    statuses__status__in=paystub_status)

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

            project_qs = project_qs.annotate(
                custom_status=Case(
                    When(statuses__status="pending", then=Value("1_pending")),
                    When(statuses__status="updated", then=Value("2_updated")),
                    When(statuses__status="rejected", then=Value("3_rejected")),
                    When(statuses__status="approved", then=Value("4_approved")),
                    default=Value("5_other"),
                    output_field=CharField(),
                )
            ).order_by("id", "custom_status").distinct("id")


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
class FinanceTimeSheetViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
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
                if 'pending' in timesheet_status:
                    timesheet_status.remove('pending')
                    timesheet_status.apppned(['submitted', 'updated'])
                paystub_qs = timesheet_qs.filter(
                    statuses__status__in=timesheet_status)
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
            project_status = request.GET.get('project_status', [])
            timesheet_status = request.GET.get('timesheet_status', [])

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
                if 'terminated' in project_status:
                    project_status.apppned(terminated_status)
                project_qs = project_qs.filter(
                        statuses__status__in=terminated_status + ['joined', 'complete'] )
            if timesheet_status:
                if 'pending' in timesheet_status:
                    timesheet_status.remove('pending')
                    timesheet_status.apppned(['submitted','updated'])
                project_qs = project_qs.filter(
                    statuses__status__in=timesheet_status)

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

            project_qs = project_qs.annotate(
                custom_status=Case(
                    When(statuses__status="pending", then=Value("1_pending")),
                    When(statuses__status="updated", then=Value("2_updated")),
                    When(statuses__status="rejected", then=Value("3_rejected")),
                    When(statuses__status="approved", then=Value("4_approved")),
                    default=Value("5_other"),
                    output_field=CharField(),
                )
            ).order_by("id", "custom_status").distinct("id")

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
        leave_status = request.GET.get('leave_status', [])
        leave_type = request.GET.get('leave_type', [])
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
                consultants=consultants.filter(leaves__status__in=leave_status)

            if leave_type:
                consultants = consultants.filter(leaves__leave_type__leave_type__in=leave_type)

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

            status_order = {
                'approved': 1,
                'rejected': 2,
                'applied': 3,
                'pending': 4,
                'rejected_1st_level': 5,
            }

            # Function to get sorting key for a consultant
            def consultant_sort_key(consultant):
                leave_status = consultant.leaves.latest().status if consultant.leaves.count() != 0 else ""
                return status_order.get(leave_status, 6), consultant.id

            # Sort the consultants based on the custom key
            sorted_consultants = sorted(consultants, key=consultant_sort_key)

            consultant_list=[]


            for consultant in sorted_consultants:
                consultant = {
                    "id":consultant.id,
                    "name":consultant.name,
                    "email":consultant.email,
                    "employer":"Boto3",
                    "approval_required":consultant.approval_required,
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
