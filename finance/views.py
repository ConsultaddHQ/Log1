import json
from datetime import datetime, date, timedelta

from constance import config
from activity.views import create_activity

from django.utils import timezone
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.db.models import Case, When, Value, CharField
from django.contrib.contenttypes.models import ContentType

from rest_framework.mixins import *
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from legal.models import Petition
from utils_app.models import Choice
from notification.models import Notification, FCMDevice
from consultant.models import Consultant, PayrollEmployer
from project.models import Project, Leave, TimeSheet, TimesheetRequest, ConsultantLeave

from project.serializers import ConsultantLeaveSerializer
from finance.serializers import FinanceDetailSerializer, FinanceSerializer, LeaveSerializer, \
    TimesheetRequestSerializer

from utils_app.thred_mail import send_email as send_email_
from notification.utils import push_notification_consultant
from project.utils import create_notification_and_send_push
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from finance.utils import check_access, make_unique_preserve_order, return_leave_status


# Route - /finance_payStubs
class FinancePayStubsViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = FinanceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            check_access(request)
            first, last = get_page_limits(request)
            filter_json = json.loads(request.GET.get('filter_json', '{}'))
            project_id = kwargs.get('pk', None)

            paystub_qs = TimeSheet.objects.filter(project=kwargs.get('pk', None)).exclude(status="draft").order_by('-created')

            if filter_json:
                if 'start' in filter_json:
                    paystub_qs = paystub_qs.filter(start__gte=filter_json.get('start'))

                if 'end' in filter_json:
                    paystub_qs = paystub_qs.filter(end__lte=filter_json['end'])

                if 'paystub_status' in filter_json:
                    paystub_status = filter_json.get('paystub_status', [])

                    if 'pending' in paystub_status:
                        paystub_status.remove('pending')
                        paystub_status.extend(['submitted', 'updated'])

                    paystub_qs = paystub_qs.filter(status__in=paystub_status)

            custom_order = Case(
                When(status='submitted', then=Value(1)),
                When(status='updated', then=Value(2)),
                When(status='rejected', then=Value(3)),
                When(status='approved', then=Value(4)),
                default=Value(5),
                output_field=CharField()
            )

            paystub_qs = paystub_qs.annotate(custom_order=custom_order).order_by('custom_order', '-created')

            total = paystub_qs.count()
            project = get_object_or_404(Project, id=project_id)
            submission = project.submission

            data = {
                "project": {
                    'id': project.id,
                    'employer': project.employer,
                    'consultant_name': project.consultant.name,
                    'consultant_email': project.consultant.email,
                    'frequency': project.timesheet_frequency,
                    'status': "terminated" if project.statuses.filter(
                        status__istartswith='terminated') else project.status,
                    'start_date': project.start_date,
                    'submission': {
                        'consultant_id': project.submission.consultant.id,
                        'consultant': project.submission.consultant.name,
                        'client': submission.client,
                        'vendor': submission.lead.vendor_company.name,
                        'work_type': submission.get_work_type_display(),
                    },
                    "paystubs": FinanceDetailSerializer(paystub_qs[first:last], many=True).data
                },
            }
            return Response({"data": data, 'total': total}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            check_access(request)
            query = request.GET.get('query', '')
            filter_json = json.loads(request.GET.get('filter_json', '{}'))
            context_data = {'timesheet_status': None, "timesheet": False}

            terminated_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue',
                'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            project_qs = Project.objects.filter(
                submission__work_type__in=['w2','full_time'], timesheets__isnull=False
            )

            pending_paystubs = project_qs.filter(timesheets__status__in=["updated", "submitted"]).order_by(
                'timesheets__id').distinct('timesheets__id').count()

            if query:
                query = query.lstrip().replace(':amp:', '&')
                project_qs = project_qs.filter(
                    Q(employer__istartswith=query) |
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            if filter_json:
                if 'client' in filter_json:
                    project_qs = project_qs.filter(submission__client__in=filter_json.get('client'))

                if 'vendor' in filter_json:
                    project_qs = project_qs.filter(submission__lead__vendor_company__name__in=filter_json.get('vendor'))

                if 'project_status' in filter_json:
                    project_status = filter_json.get('project_status', [])
                    if 'terminated' in project_status:
                        project_status.extend(terminated_status)
                    if 'active' in filter_json.get('project_status'):
                        project_status.append('joined')

                    project_qs = project_qs.filter(statuses__status__in=project_status, statuses__is_current=True)

                if 'paystub_status' in filter_json:
                    paystub_status = filter_json['paystub_status'].split(',')
                    context_data['timesheet_status'] = paystub_status

                    if 'pending' in paystub_status:
                        paystub_status.extend(['submitted', 'updated'])

                    project_qs = project_qs.filter(timesheets__status__in=paystub_status)

                    if 'pending' in paystub_status:
                        paystub_status.remove('submitted')
                        paystub_status.remove('updated')

                if "paystub_frequency" in filter_json:
                    capitalize_frequencies = [frequency.capitalize() for frequency in
                                              filter_json.get('paystub_frequency')]
                    project_qs = project_qs.filter(timesheet_frequency__in=capitalize_frequencies)

                if 'start' in filter_json:
                    project_qs = project_qs.filter(timesheets__start__gte=filter_json.get('start'))

                if 'end' in filter_json:
                    project_qs = project_qs.filter(timesheets__end__lte=filter_json.get('end'))

                if 'unsubmitted_paystubs' in filter_json:
                    today = datetime.today()
                    days_until_monday = today.weekday() + 1  # Monday is 0, Sunday is 6
                    start_date = today - timedelta(days=days_until_monday) - timedelta(weeks=2)
                    end_date = start_date + timedelta(weeks=2) - timedelta(days=1)

                    weekly_qs = project_qs.filter(timesheet_frequency="Weekly").exclude(
                        timesheets__start__gte=start_date, timesheets__start__lte=end_date).distinct()
                    biweekly_qs = project_qs.filter(timesheet_frequency="Biweekly").exclude(
                        timesheets__start__gte=today-timedelta(days=20), timesheets__start__lte=today).distinct()
                    monthly_qs = project_qs.filter(timesheet_frequency="Monthly").exclude(
                        timesheets__start__gte=today - timedelta(days=35),timesheets__start__lte=today).distinct()

                    project_qs = (weekly_qs | biweekly_qs | monthly_qs)


            project_qs = project_qs.annotate(
                timesheet_status=Case(
                    When(timesheets__status='updated', then=Value(1)),
                    When(timesheets__status='submitted', then=Value(2)),
                    When(timesheets__status='rejected', then=Value(3)),
                    When(timesheets__status='approved', then=Value(4)),
                    When(timesheets__status='draft', then=Value(5)),
                    default=Value(6),
                    output_field=CharField()
                )
            )

            duplicate_project_ids = project_qs.order_by('timesheet_status').values_list('id', flat=True)
            distinct_project_ids = make_unique_preserve_order(duplicate_project_ids)
            id_to_order = {id: order for order, id in enumerate(distinct_project_ids)}
            custom_order_queryset = Project.objects.filter(id__in=id_to_order)
            custom_order_queryset = sorted(custom_order_queryset, key=lambda x: id_to_order[x.id])

            project_serializer = FinanceSerializer(custom_order_queryset[first:last], many=True, context=context_data)

            data = {
                "pending_paystubs": pending_paystubs,
                "project_list": project_serializer.data,
                "total": len(custom_order_queryset)
            }
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            check_access(request)
            paystub_id = kwargs.get('pk')
            paystub = get_object_or_404(TimeSheet, id=paystub_id)
            paystub.remark = request.data.get('remark', None)
            paystub.status = request.data.get('status')
            paystub.status_updated_at = timezone.now()
            paystub.status_updated_by = request.user
            paystub.save()
            notification_type = "rejected" if request.data.get('status') == 'rejected' else "Approved"
            create_notification_and_send_push(paystub, request, notification_type)
            serializer = self.serializer_class(paystub)
            return Response({"data": serializer.data, "message": "PayStubs is updated"},
                            status=status.HTTP_202_ACCEPTED)
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
        try:
            check_access(request)
            filter_json = json.loads(request.GET.get('filter_json', '{}'))
            project_id = kwargs.get('pk', None)
            timesheet_qs = TimeSheet.objects.filter(project=project_id).order_by('-created')

            if filter_json:

                if 'start' in filter_json:
                    timesheet_qs = timesheet_qs.filter(start__gte=filter_json.get('start'))

                if 'end' in filter_json:
                    timesheet_qs = timesheet_qs.filter(end__lte=filter_json['end'])

                if 'timesheet_status' in filter_json:
                    timesheet_status = filter_json.get('timesheet_status')
                    if 'pending' in timesheet_status:
                        timesheet_status.remove('pending')
                        timesheet_status.extend(['submitted', 'updated'])
                    timesheet_qs = timesheet_qs.filter(status__in=timesheet_status)
                else:
                    timesheet_qs = timesheet_qs.exclude(status='draft')

            custom_order = Case(
                When(status='submitted', then=Value(1)),
                When(status='updated', then=Value(2)),
                When(status='rejected', then=Value(3)),
                When(status='approved', then=Value(4)),
                When(status='draft', then=Value(5)),
                default=Value(6),
                output_field=CharField()
            )

            # Order the queryset based on custom_order and created date
            timesheet_qs = timesheet_qs.annotate(custom_order=custom_order).order_by('custom_order', '-created')
            total = timesheet_qs.count()
            project = Project.objects.get(id=project_id)
            data = {
                "project": {
                    'id': project.id,
                    'employer': project.employer,
                    'consultant_name': project.consultant.name,
                    'consultant_email': project.consultant.email,
                    'frequency': project.timesheet_frequency,
                    'status': "terminated" if project.statuses.filter(
                        status__istartswith='terminated') else project.status,
                    'start_date': project.start_date,
                    'submission': {
                        'consultant_id': project.submission.consultant.id,
                        'consultant': project.submission.consultant.name,
                        'client': project.submission.client,
                        'vendor': project.submission.lead.vendor_company.name,
                        'work_type': project.submission.get_work_type_display(),
                    },
                    "timesheets": FinanceDetailSerializer(timesheet_qs[first:last], many=True).data
                },
            }

            return Response({"data": data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            check_access(request)
            query = request.GET.get('query', '')
            filter_json = json.loads(request.GET.get('filter_json', '{}'))
            context_data = {'timesheet_status': None, 'timesheet': True}

            terminated_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue',
                'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            project_qs = Project.objects.filter(
                submission__work_type="c2c", timesheets__isnull=False
            )
            pending_timesheet = project_qs.filter(timesheets__status__in=["updated", "submitted"]).order_by(
                'timesheets__id').distinct('timesheets__id').count()

            request_timesheet = project_qs.filter(timesheet_requests__status="request").order_by(
                'timesheet_requests__id').distinct('timesheet_requests__id').count()

            if filter_json:
                if 'client' in filter_json:
                    project_qs = project_qs.filter(submission__client__in=filter_json.get('client'))

                if 'vendor' in filter_json:
                    project_qs = project_qs.filter(submission__lead__vendor_company__name__in=filter_json.get('vendor'))

                if 'project_status' in filter_json:
                    project_status = filter_json.get('project_status')
                    if 'terminated' in project_status:
                        project_status.extend(terminated_status)
                    if 'active' in project_status:
                        project_status.append('joined')
                    project_qs = project_qs.filter(
                        statuses__status__in=project_status, statuses__is_current=True)

                if 'timesheet_status' in filter_json:
                    timesheet_status = filter_json.get('timesheet_status').split(',')
                    context_data['timesheet_status'] = timesheet_status
                    if 'pending' in timesheet_status:
                        timesheet_status.extend(['submitted', 'updated'])
                    project_qs = project_qs.filter(
                        timesheets__status__in=timesheet_status)
                    if 'pending' in timesheet_status:
                        timesheet_status.remove('submitted')
                        timesheet_status.remove('updated')

                if 'start' in filter_json:
                    project_qs = project_qs.filter(timesheets__start__gte=filter_json.get('start'))

                if 'end' in filter_json:
                    project_qs = project_qs.filter(timesheets__end__lte=filter_json.get('end'))

                if 'request_timesheet' in filter_json:
                    project_qs = project_qs.filter(timesheet_requests__status='request')

                if 'unsubmitted_timesheet' in filter_json:
                    today = datetime.today()
                    days_until_monday = today.weekday() + 1  # Monday is 0, Sunday is 6
                    start_date = today - timedelta(days=days_until_monday) - timedelta(weeks=2)
                    end_date = today - timedelta(days=1)
                    project_qs = project_qs.filter().exclude(timesheets__start__gte=start_date, timesheets__start__lte=end_date,
                                                   timesheets__status__in=["approved","rejected","submitted"]).distinct()


            if query:
                query = query.lstrip().replace(':amp:', '&')
                project_qs = project_qs.filter(
                    Q(employer__istartswith=query) |
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            project_qs = project_qs.annotate(
                timesheet_status=Case(
                    When(timesheets__status='updated', then=Value(1)),
                    When(timesheets__status='submitted', then=Value(2)),
                    When(timesheets__status='rejected', then=Value(3)),
                    When(timesheets__status='approved', then=Value(4)),
                    When(timesheets__status='draft', then=Value(5)),
                    default=Value(6),
                    output_field=CharField()
                )
            )

            # Order the projects by the timesheet status in ascending order.
            duplicate_project_ids = project_qs.order_by('timesheet_status').values_list('id', flat=True)
            distinct_project_ids = make_unique_preserve_order(duplicate_project_ids)
            id_to_order = {id: order for order, id in enumerate(distinct_project_ids)}
            custom_order_queryset = Project.objects.filter(id__in=id_to_order)
            custom_order_queryset = sorted(custom_order_queryset, key=lambda x: id_to_order[x.id])

            project_serializer = FinanceSerializer(custom_order_queryset[first:last], many=True, context=context_data)

            data = {
                "pending_timesheet": pending_timesheet,
                "request_timesheet": request_timesheet,
                "project_list": project_serializer.data,
                "total": len(custom_order_queryset),
            }
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            check_access(request)
            timesheet_id = kwargs.get('pk')
            timesheet = get_object_or_404(TimeSheet, id=timesheet_id)
            timesheet.remark = request.data.get('remark', None)
            timesheet.status = request.data.get('status')
            timesheet.status_updated_at = datetime.now()
            timesheet.status_updated_by = request.user
            timesheet.save()
            notification_type = "rejected" if request.data.get('status') == 'rejected' else "Approved"
            create_notification_and_send_push(timesheet, request, notification_type)
            serializer = FinanceDetailSerializer(timesheet)
            return Response({"data": serializer.data, "message": "Timesheet is updated"},
                            status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(methods=["post"], detail=False, url_name="send_reminder")
    def send_reminder(self, request, *args, **kwargs):
        check_access(request)
        project_ids = request.data.get('project_ids', [])
        timesheet_ids = request.data.get('timesheet_ids', [])
        start = request.data.get('start', None)
        end = request.data.get('end', None)

        if not project_ids and not timesheet_ids:
            return Response({"message": "Mail not sent"}, status=status.HTTP_400_BAD_REQUEST)

        cc = [config.FINANCE, 'yash.j@consultadd.com']
        bcc = []

        if project_ids:
            timesheet_data = []
            for project_id in project_ids:
                project = Project.objects.get(id=project_id)
                work_type = project.submission.work_type

                mail_data = {
                    'cc': cc,
                    'bcc': bcc,
                    'template': '../templates/reminder.html',
                    'to': [project.consultant.email],
                    'context': {
                        'consultant': project.consultant.name,
                    }
                }
                if work_type=='c2c':
                    timesheets = TimeSheet.objects.filter(
                        status='draft',
                        project=project,
                        is_active=True,
                    ).order_by('-created')[:2]

                    if start is not None:
                        timesheets = timesheets.filter(start__gte=start)

                    if end is not None:
                        timesheets = timesheets.filter(end__lte=end)

                    mail_data['context']['timesheet_list'] = timesheets if timesheets else None
                    mail_data['subject'] = "Timesheet reminder"
                    mail_data['context']['work_type'] = "Timesheet"
                else:
                    mail_data['context']['timesheet_list'] = None
                    mail_data['subject'] = "Paystubs reminder"
                    mail_data['context']['work_type'] = "Paystubs"

                send_email_(mail_data, 'sakshi.shetty@consultadd.com', request=request)

        else:
            timesheets = TimeSheet.objects.filter(id__in=timesheet_ids)
            consultant_email = timesheets[0].project.consultant.email
            mail_data = {
                'cc': cc,
                'bcc': bcc,
                'template': '../templates/reminder.html',
                'to': [consultant_email],
                'subject': "Timesheet reminder",
                'context': {
                    'consultant': timesheets[0].project.consultant.name,
                    'timesheet_list': timesheets,
                }
            }
            send_email_(mail_data, 'sakshi.shetty@consultadd.com', request=request)

        return Response({"message": "Mail sent"}, status=status.HTTP_202_ACCEPTED)

    @action(methods=["get"], detail=True, url_name="projects")
    def projects(self, request, *args, **kwargs):
        try:
            check_access(request)
            consultant_id = kwargs.get('pk', None)
            is_c2c = request.GET.get('timesheet', 'true')

            if consultant_id is None or is_c2c is None:
                return Response({'message': "Projects Not Found"}, status=status.HTTP_400_BAD_REQUEST)

            if json.loads(is_c2c):
                work_type = ['c2c']
            else:
                work_type = ['w2','full_time']

            projects = Project.objects.filter(
                Q(consultant_id=consultant_id, statuses__is_current=True, submission__work_type__in=work_type) & (
                        Q(statuses__status='joined') |
                        Q(statuses__status__istartswith='terminated') |
                        Q(statuses__status__in=['complete', 'extended'])
                )
            ).annotate(
                client=F('submission__client'),
                work_type=F('submission__work_type'),
                remote_engineer=F('consultant__name'),
                remote_engineer_email=F('consultant__email'),
                vendor=F('submission__lead__vendor_company__name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'client', 'vendor', 'work_type', 'remote_engineer', 'remote_engineer_email',
                     'consultant_name').order_by('id', '-start_date').distinct('id')
            return Response({'result': projects, 'total': projects.count()}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["GET", "PUT"], detail=True, url_name="request_timesheet")
    def request_timesheet(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            check_access(request)
            if request.method == 'GET':
                filter_json = json.loads(request.GET.get('filter_json', '{}'))
                project_id = kwargs.get('pk', None)
                if not project_id:
                    return Response({"error": "project not available"}, status=status.HTTP_400_BAD_REQUEST)
                requested_timesheets = TimesheetRequest.objects.filter(project=project_id)

                if 'timesheet_status' in filter_json:
                    if "pending" in filter_json['timesheet_status']:
                        filter_json['timesheet_status'].append("request")
                    if "approved" in filter_json['timesheet_status']:
                        filter_json['timesheet_status'].append("accepted")
                    if "rejected" in filter_json['timesheet_status']:
                        filter_json['timesheet_status'].append("reject")
                    requested_timesheets = requested_timesheets.filter(status__in=filter_json['timesheet_status'])

                if 'start' in filter_json:
                    requested_timesheets = requested_timesheets.filter(start__gte=filter_json['start'])

                if 'end' in filter_json:
                    requested_timesheets = requested_timesheets.filter(end__lte=filter_json['end'])

                custom_order = Case(
                    When(status='request', then=Value(1)),
                    When(status='reject', then=Value(2)),
                    When(status='accepted', then=Value(3)),
                    default=Value(6),
                    output_field=CharField()
                )

                # Order the queryset based on custom_order and created date
                requested_timesheets = requested_timesheets.annotate(
                    custom_order=custom_order).order_by('custom_order', '-created')

                total = requested_timesheets.count()

                project = Project.objects.get(id=project_id)
                data = {
                    "project": {
                        'id': project.id,
                        'employer': project.employer,
                        'consultant_name': project.consultant.name,
                        'consultant_email': project.consultant.email,
                        'frequency': project.timesheet_frequency,
                        'status': "terminated" if project.statuses.filter(
                            status__istartswith='terminated') else project.status,
                        'start_date': project.start_date,
                        'submission': {
                            'consultant_id': project.submission.consultant.id,
                            'consultant': project.submission.consultant.name,
                            'client': project.submission.client,
                            'vendor': project.submission.lead.vendor_company.name,
                            'work_type': project.submission.get_work_type_display(),
                        },
                        "timesheets": TimesheetRequestSerializer(requested_timesheets[first:last], many=True).data
                    },
                }

                return Response({"data": data, 'total': total}, status=status.HTTP_200_OK)

            elif request.method == 'PUT':
                request_id = kwargs.get('pk', None)
                timesheet_status = request.data.get('status', None)

                if request_id is None or timesheet_status is None:
                    return Response({"message": "Requested timesheet not found"}, status=status.HTTP_400_BAD_REQUEST)

                timesheet = get_object_or_404(TimesheetRequest, id=request_id)

                available_timesheet = TimeSheet.objects.filter(project=timesheet.project, end__gte=timesheet.start
                                                               ).order_by('-created')
                if available_timesheet:
                    timesheet.status = 'reject'
                    timesheet.save()
                    timesheet = available_timesheet.first()
                    available_week = f"{timesheet.start} - {timesheet.end}"
                    return Response({"message": f"Timesheet available for week {available_week}"}, status=status.HTTP_400_BAD_REQUEST)

                timesheet.reviewed_by = request.user
                timesheet.status = "accepted" if timesheet_status == "approved" else "reject"
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

                return Response({"message": f"TimeSheet request {timesheet.get_status_display()}"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

# Route - /finance_leave
class FinanceLeaveViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        filter_json = json.loads(request.GET.get('filter_json', '{}'))
        query = request.GET.get('query', None)

        try:
            check_access(request)
            consultants = Consultant.objects.all().exclude(status='terminated')

            data = {
                "pending_level_2": Leave.objects.filter(consultant__in=consultants, status='applied').count(),
                "pending_level_1": Leave.objects.filter(consultant__in=consultants, status='pending').count(),
                "rejected_level_1": Leave.objects.filter(consultant__in=consultants,
                                                         status='rejected_1st_level').count(),
            }

            if filter_json:
                if 'leave_status' in filter_json:
                    consultants = consultants.filter(leaves__status=filter_json.get('leave_status'))

                if 'leave_type' in filter_json:
                    consultants = consultants.filter(leaves__leave_type__leave_type__name__in=filter_json.get('leave_type'))

                if 'approval_required' in filter_json:
                    consultants = consultants.filter(approval_required=filter_json.get('approval_required'))

                if 'start' in filter_json:
                    consultants = consultants.filter(leaves__from_date__gte=filter_json.get('start'))

                if 'end' in filter_json:
                    consultants = consultants.filter(leaves__to_date__lte=filter_json.get('end'))

            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = consultants.filter(
                    Q(name__istartswith=query) |
                    Q(email__istartswith=query)
                )

            consultants = consultants.annotate(
                custom_order=Case(
                    When(leaves__status='pending', then=Value(1)),
                    When(leaves__status='applied', then=Value(2)),
                    When(leaves__status='rejected_1st_level', then=Value(3)),
                    When(leaves__status='rejected', then=Value(4)),
                    When(leaves__status='approved', then=Value(5)),
                    default=Value(6),
                    output_field=CharField()
                )
            )

            # Order the queryset based on custom_order and created date
            # consultants = consultants.annotate(custom_order=custom_order).order_by('custom_order', '-created')

            duplicate_project_ids = consultants.order_by('custom_order').values_list('id', flat=True)
            distinct_project_ids = make_unique_preserve_order(duplicate_project_ids)
            id_to_order = {id: order for order, id in enumerate(distinct_project_ids)}
            custom_order_queryset = Consultant.objects.filter(id__in=id_to_order)
            consultants = sorted(custom_order_queryset, key=lambda x: id_to_order[x.id])

            consultant_list = []

            for consultant in consultants[first:last]:
                employers = PayrollEmployer.objects.filter(consultant=consultant).order_by('-created')
                consultant = {
                    "id": consultant.id,
                    "name": consultant.name,
                    "email": consultant.email,
                    "approval_required": consultant.approval_required,
                    "employer": employers.first().name if employers.first() else None,
                    "leave_status": return_leave_status(filter_json['leave_status'],consultant) if 'leave_status' in filter_json
                    else return_leave_status(None,consultant) if consultant.leaves.exists() else None,
                    "leave_type": consultant.leaves.latest().leave_type.leave_type.name if consultant.leaves.count() != 0 else None,
                }
                consultant_list.append(consultant)

            data["consultants"] = consultant_list

            total = len(consultants)
            # serializer = ConsultantTimeSheetSerializer(consultants[first:last], many=True)
            return Response({"data": data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            check_access(request)
            filter_json = json.loads(request.GET.get('filter_json', '{}'))
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk', None))
            leave_qs = self.queryset.filter(consultant=consultant).order_by('-created')

            if filter_json:
                if 'end' in filter_json:
                    leave_qs = leave_qs.filter(to_date__lte=filter_json.get('end'))
                if 'start' in filter_json:
                    leave_qs = leave_qs.filter(from_date__gte=filter_json.get('start'))
                if 'leave_status' in filter_json:
                    leave_qs = leave_qs.filter(status__in=filter_json.get('leave_status'))
                if 'leave_type' in filter_json:
                    leave_qs = leave_qs.filter(leave_type__leave_type__name__in=filter_json.get('leave_type'))

            custom_order = Case(
                When(status='pending', then=Value(1)),
                When(status='applied', then=Value(2)),
                When(status='rejected_1st_level', then=Value(3)),
                When(status='rejected', then=Value(4)),
                When(status='approved', then=Value(5)),
                default=Value(6),
                output_field=CharField()
            )

            # Order the queryset based on custom_order and created date
            leave_qs = leave_qs.annotate(custom_order=custom_order).order_by('custom_order', '-created')
            petition = Petition.objects.filter(beneficiary=consultant, is_active=True).first()
            data = {
                "id":consultant.id,
                "name":consultant.name,
                "email":consultant.email,
                "team": petition.employer if petition else None,
                "approval_required":consultant.approval_required,
                "leaves":LeaveSerializer(leave_qs[first:last], many=True).data
            }
            return Response({"data": data, 'total': len(leave_qs)}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        consultant = get_object_or_404(Consultant, id=kwargs.get('consultant_id'))

        try:
            check_access(request)
            leave_status = request.data.get('status', None)
            if not leave_status:
                return Response({"error": "No action selected"}, status=status.HTTP_400_BAD_REQUEST)

            leave = get_object_or_404(Leave, id=kwargs.get('pk'), consultant=consultant)
            prev_status = leave.get_status_display()
            leave.remarks = request.data.get('remarks', None)
            leave.save()

            consultant_leave = leave.leave_type
            if not leave_status or leave_status == leave.status:
                return Response({"error": "Status Not Updated"}, status=status.HTTP_400_BAD_REQUEST)

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
                title = f"Leave initial level approval granted"
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

            return Response({"message": "Leave updated successfully"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["put"], detail=False, url_name="approval_required")
    def approval_required(self, request, *args, **kwargs):
        try:
            check_access(request)
            approval = request.data.get('action', True)
            count = 0
            consultant_ids = request.data.get('consultant_ids', [])
            message =  "Consultant Approval Updated"

            for consultant_id in consultant_ids:
                exit_pending = Leave.objects.filter(consultant=consultant_id, status__in=['pending', 'applied'])
                if exit_pending:
                    count += 1
                    if count > 1:
                        message = "Consultants have pending leave. Kindly update then change the 2L leave approval"
                    else:
                        message = "Consultant has pending leave. Kindly update then change the 2L leave approval"
                else:
                    consultant = Consultant.objects.get(id=consultant_id)
                    if consultant.approval_required == approval:
                        continue
                    consultant.approval_required = approval
                    consultant.save()

                    # updated_consultants = updated_consultants + consultant.name + ' '
                    required = '' if approval else 'not '
                    desc = f"{request.user.employee_name} marked {consultant.name} approval as {required}required"
                    create_activity(consultant.id, 'leave', request.user, desc, 'updated')

                if message is None:
                    message = "Consultant Approval Updated"

            return Response({"message": message}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveBalanceViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ConsultantLeave.objects.all()
    serializer_class = ConsultantLeaveSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            check_access(request)
            leaves = request.data.get('leave', [])
            consultant_id = request.data.get('consultant_id')

            for leave in leaves:
                leave_exit = ConsultantLeave.objects.filter(
                    consultant_id=consultant_id, year=leave.get('year', date.today().year), leave_type=leave.get('id')
                )
                if leave_exit:
                    continue
                # disable the previous leave if exit
                ConsultantLeave.objects.filter(consultant_id=consultant_id, leave_type=leave.get('id')).update(
                    is_expired=True)

                new_balance = ConsultantLeave(
                    year=leave.get('year', date.today().year),
                    balance=leave.get('balance', 0.0),
                    granted=leave.get('balance', 0.0),
                    is_expired=False,
                    leave_type=Choice.objects.get(id=leave.get('id')),
                    consultant_id=consultant_id
                )
                new_balance.save()

            return Response({"message": "Leave balances created"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            check_access(request)
            year = request.GET.get('year', date.today().year)
            queryset = ConsultantLeave.objects.filter(consultant__id=kwargs.get('pk'), year=year)

            queryset = queryset.annotate(
                leave=Case(
                    When(leave_type__name='sick_leave', then=Value(1)),
                    When(leave_type__name='pto', then=Value(2)),
                    When(leave_type__name='marriage_leave', then=Value(3)),
                    When(leave_type__name='maternity', then=Value(4)),
                    When(leave_type__name='paternity', then=Value(5)),
                    default=Value(6),
                    output_field=CharField()
                )
            )
            queryset = queryset.order_by('leave')
            # queryset = ConsultantLeave.objects.filter(consultant_id=consultant_id)
            serializer = ConsultantLeaveSerializer(queryset[first:last], many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            check_access(request)
            leave_type = get_object_or_404(ConsultantLeave, id=kwargs.get('pk'))
            update_balance = request.data.get('granted_leaves', 0)

            diff = update_balance - leave_type.balance
            leave_type.balance += diff
            leave_type.granted += diff
            leave_type.save()

            sender_content_type = ContentType.objects.get(model='user')
            target_content_type = ContentType.objects.get(model='leave')
            recipient_content_type = ContentType.objects.get(model='consultant')
            title = f"{leave_type.leave_type.display_name} balance updated"

            Notification.objects.create(
                title=title, recipient_object_id=leave_type.consultant.id,
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

            return Response({"message": "Leave balance updated"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            check_access(request)
            ConsultantLeave.objects.get(id=kwargs.get('pk')).delete()
            return Response({"message": "Leave balance deleted"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)