import os
import json
from datetime import datetime, date

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import F, Q, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin

from constance import config
from log1.utils import ERROR_MSG
from utils_app.models import ObjectGroup
from api_key.permissions import HasAPIKey
from activity.views import create_activity
from marketing.models import Submission, User
from attachment.models import create_attachment
from utils_app.utils import get_attachment_status
from consultant.models import ConsultantPOC, Consultant
from notification.models import Notification, FCMDevice
from attachment.views import download_s3_object, delete_temp_file
from utils_app.mailing import send_email_attachment_multiple, send_email
from log1.utils import get_time_filter, get_page_limits, write_exception
from project.utils import ProjectUtil, create_remote_consultant, set_consultant_password
from notification.utils import create_notification, push_notification, push_notification_consultant
from project.models import Project, ProjectStatus, ProjectOrder, TimeSheet, ProjectSupport, SupportStatus
from project.serializers import ProjectSerializer, ProjectGetSerializer, ProjectOrderSerializer, FinanceSerializer, \
    ProjectSupportSerializer, ConsultantTimeSheetSerializer


# Route - /project/
class ProjectViewSets(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def fetch_scrum_masters(self, request):
        scrum_masters = list(User.objects.filter(
            team=request.user.team, role__name__in=['admin', 'proxy'], is_active=True
        ).values_list('email', flat=True))
        return scrum_masters

    def consultant_mail_on_joining(self, project, password, new_user):
        try:
            mail_data = {
                'to': [project.consultant.email],
                'cc': [config.FINANCE],
                'bcc': [],
                'template': '../templates/consultant_account_creation.html',
                'subject': f'Your account created on Consultadd Time Track App',
                'context': {
                    'password': password,
                    'new_user': new_user,
                    'iphone_link': config.IPHONE_APP_LINK,
                    'android_link': config.ANDROID_APP_LINK,
                    'consultant_name': project.consultant.name,
                    'client': project.submission.client.title(),
                    'consultant_email': project.consultant.email,
                },
            }
            res = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res = send_email(mail_data, config.RELATIONS)
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    def send_offer_received_mail(self, project, scrum_masters):
        try:
            submission = project.submission
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, submission.created_by.team.email]

            cc = [config.SUPERADMIN, submission.created_by.email] + scrum_masters

            consultant = project.submission.consultant
            recruiter = consultant.recruiter
            retention = consultant.relation
            if recruiter:
                cc.append(recruiter.email)

            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')

            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'template': '../templates/offer.html',
                'subject': f'Offer Received of {consultant.name} :: {submission.client} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'context': {
                    'rate': project.rate,
                    'start': project_start_date,
                    'con_rate': consultant.rate,
                    'employer': project.employer,
                    'client_name': submission.client,
                    'consultant_name': consultant.name,
                    'consultant_email': consultant.email,
                    'job_title': submission.lead.job_title,
                    'vendor_company': submission.vendor.name,
                    'marketer_name': submission.created_by.employee_name,
                },
            }

            res = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res = send_email(mail_data, submission.created_by.email)

            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    def send_support_mail(self, project, scrum_masters):
        try:
            submission = project.submission
            path, recordings = [], []
            resume = submission.attachments.filter(attachment_type='resume')

            recordings = [interview.attachment_link for interview in submission.screening.all()
                          if interview.attachment_link is not None]
            recordings = ", ".join(recordings) if len(recordings) != 0 else "NA"

            notes = [interview.notes for interview in submission.screening.all() if interview.notes is not None]
            notes = "\n".join(notes) if len(notes) != 0 else "NA"

            if resume:
                path.append(download_s3_object(resume.first().attachment_file.name))

            consultant = project.submission.consultant
            recruiter = consultant.recruiter
            retention = consultant.relation
            cc = [config.RECRUITMENT, config.RELATIONS, submission.created_by.team.email, submission.created_by.email]
            cc = cc + scrum_masters

            recruiter_name = "NA"
            if recruiter:
                recruiter_name = recruiter.employee_name
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')

            mail_data = {
                'cc': cc,
                'bcc': [],
                'attachments': path,
                'to': [config.ENGINEERING],
                'template': '../templates/support.html',
                'subject': f'Support Initiation for {consultant.name} {submission.client} {submission.lead.city}',
                'context': {
                    'notes': notes,
                    'recordings': recordings,
                    'start': project_start_date,
                    'employer': project.employer,
                    'client_name': submission.client,
                    'location': submission.lead.city,
                    'recruiter_name': recruiter_name,
                    'consultant_name': consultant.name,
                    'consultant_email': consultant.email,
                    'job_title': submission.lead.job_title,
                    'consultant_phone_no': consultant.phone_no,
                    'consultant_location': consultant.current_city,
                    'marketer_name': submission.created_by.employee_name,
                    'jd': submission.lead.job_desc.replace("\n", " ;newline; "),
                },
            }

            res = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res = send_email_attachment_multiple(mail_data, submission.created_by.email)

            delete_temp_file(path)
            return res, "ok"
        except Exception as error:
            return error, "error"

    def send_support_offer_mail(self, project, scrum_masters):
        support_res, support_msg = self.send_support_mail(project, scrum_masters)
        offer_res, offer_msg = self.send_offer_received_mail(project, scrum_masters)

        message = "Project created"
        exception_msg = "Mail sent"
        if support_msg == 'error' and offer_msg == 'error':
            message = "Project created, but unable to send Support and Offer mail"
            exception_msg = f"Support: {support_res}, Offer: {offer_res}"
            write_exception(message=exception_msg)
        elif support_msg == 'error':
            message = "Project created, but unable to send Support mail"
            exception_msg = f"Support: {support_res}"
            write_exception(message=exception_msg)
        elif offer_msg == 'error':
            message = "Project created, but unable to send Offer mail"
            exception_msg = f"Offer: {offer_res}"
            write_exception(message=exception_msg)

        return message, exception_msg

    def po_mail(self, project, path, scrum_master_email, po_type):
        submission = project.submission
        marketer = submission.created_by
        consultant = project.submission.consultant
        try:
            vendor_contact = submission.vendor_contact
            if not vendor_contact:
                return "Vendor is empty", 'error'

            recruiter = consultant.recruiter
            retention = consultant.relation
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL, marketer.team.email]
            cc = [marketer.email, config.SUPERADMIN] + scrum_master_email
            if project.employer == 'Consultadd':
                to.append(config.VENDOR_MANAGEMENT)
            if recruiter:
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')

            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'attachments': path,
                'template': '../templates/po.html',
                'subject': f'On Boarding of {consultant.name} :: {project.employer} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'context': {
                    'type': po_type,
                    'rate': project.rate,
                    'start': project_start_date,
                    'employer': project.employer,
                    'client_name': submission.client,
                    'con_rate': int(consultant.rate),
                    'vendor_name': vendor_contact.name,
                    'consultant_name': consultant.name,
                    'vendor_email': vendor_contact.email,
                    'payment_term': project.payment_term,
                    'consultant_email': consultant.email,
                    'job_title': submission.lead.job_title,
                    'vendor_number': vendor_contact.number,
                    'client_address': project.client_address,
                    'vendor_address': project.vendor_address,
                    'invoicing_period': project.invoicing_period,
                    'reporting_details': project.reporting_details,
                    'marketer_name': submission.created_by.employee_name,
                    'vendor_company': submission.lead.vendor_company.name,
                },
            }

            res = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res = send_email_attachment_multiple(mail_data, marketer.email)

            return res, "ok"
        except Exception as error:
            write_exception(message=f"Offer mail error for {marketer.email}: {error}")
            return error, "error"

    def po_end_mail(self, project, scrum_master_email, po_type):
        submission = project.submission
        marketer = submission.created_by
        consultant = project.submission.consultant
        try:
            vendor = submission.vendor_contact
            if vendor:
                vendor_name = vendor.name
                vendor_email = vendor.email
                vendor_number = vendor.number
            else:
                vendor_name = None
                vendor_email = None
                vendor_number = None

            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL, marketer.team.email]
            if project.employer == 'Consultadd':
                to.append(config.VENDOR_MANAGEMENT)

            recruiter = consultant.recruiter
            retention = consultant.relation

            cc = [marketer.email, config.SUPERADMIN] + scrum_master_email
            if recruiter:
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            project_end_date = None
            if project.end_date:
                project_end_date = datetime.strptime(str(project.end_date), '%Y-%m-%d').strftime('%m/%d/%Y')

            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'template': '../templates/po_termination.html',
                'subject': f"{consultant.name}'s {po_type} :: {project.employer} :: "
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'context': {
                    'po_type': po_type,
                    'rate': project.rate,
                    'end': project_end_date,
                    'remark': project.feedback,
                    'vendor_name': vendor_name,
                    'start': project_start_date,
                    'vendor_email': vendor_email,
                    'employer': project.employer,
                    'vendor_number': vendor_number,
                    'client_name': submission.client,
                    'consultant_name': consultant.name,
                    'consultant_email': consultant.email,
                    'job_title': submission.lead.job_title,
                    'marketer_name': marketer.employee_name,
                    'vendor_address': project.vendor_address,
                    'client_address': project.client_address,
                    'reporting_details': project.reporting_details,
                    'vendor_company': submission.lead.vendor_company.name,
                    'reason': project.statuses.get(is_current=True).get_status_display(),
                }
            }
            res1 = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res1 = send_email(mail_data, marketer.email)

            mail_data_eng = {
                'cc': [],
                'bcc': [],
                'to': [config.ENGINEERING],
                'template': '../templates/po_termination_engineering.html',
                'subject': f"{consultant.name}'s {po_type} :: {project_start_date} :: {submission.client} ::"
                           f" {submission.vendor.name}",
                'context': {
                    'po_type': po_type,
                    'end': project_end_date,
                    'client_name': submission.client,
                    'consultant_name': consultant.name,
                    'consultant_email': consultant.email,
                    'vendor_company': submission.lead.vendor_company.name,
                    'reason': project.statuses.get(is_current=True).get_status_display(),
                }
            }
            res2 = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res2 = send_email(mail_data_eng, marketer.email)

            return f"Res1: {res1} and res2: {res2}", "ok"
        except Exception as error:
            write_exception(message="Offer mail error for {}".format(marketer.email) + str(error))
            return error, "error"

    def retrieve(self, request, *args, **kwargs):
        try:
            permission = {"update": False}
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            if project.submission.created_by.id == request.user.id:
                permission['update'] = True
            serializer = ProjectGetSerializer(project)
            return Response({"data": serializer.data, "permission": permission}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.query_params.get('query', None)
        version = request.query_params.get('version', 'v1')
        sort_by = request.query_params.get('sort_by', None)
        filter_for = request.query_params.get('filter_for', None)
        filter_json = request.query_params.get('filter_json', None)
        filter_by_time = request.query_params.get('filter_by_time', None)
        filter_by_lead = request.query_params.get('filter_by_lead', None)
        filter_by_status = request.query_params.get('filter_by_status', None)

        try:
            # search project by client and consultant
            if filter_for == 'my':
                projects = Project.objects.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                projects = Project.objects.filter(submission__created_by__team=request.user.team)
            else:
                projects = Project.objects.all()

            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(city__istartswith=query) |
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if version == 'v2' and filter_json:
                filter_string = dict()
                filters = json.loads(filter_json)

                if 'remote' in filters:
                    filter_string["is_remote"] = filters['remote']

                if 'w2' in filters:
                    filter_string["submission__lead__is_w2"] = filters['w2']

                if 'client' in filters and len(filters["client"]) > 0:
                    filter_string["submission__client"] = filters["client"]

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    filter_string["submission__created_by_id__in"] = filters["marketer"]

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    filter_string["submission__lead__vendor_company_id__in"] = filters["vendor"]

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    filter_string["submission__consultant_marketing__consultant_id__in"] = filters["consultant"]

                created = filters.get('created', None)
                if created:
                    lte = created.get('lte', None)
                    gte = created.get('gte', None)
                    if lte:
                        filter_string["created__lte"] = lte
                    if gte:
                        filter_string["created__gte"] = gte

                projects = projects.order_by('id').distinct('id')
                projects = projects.filter(**filter_string)
                data = {
                    "total": projects,
                    "new": projects.filter(statuses__status='new', statuses__is_current=True),
                    "joined": projects.filter(statuses__status='joined', statuses__is_current=True),
                    "received": projects.filter(statuses__status='received', statuses__is_current=True),
                    "on_boarded": projects.filter(statuses__status='on_boarded', statuses__is_current=True),
                    "not_joined": projects.filter(statuses__status='on_boarded', statuses__is_current=True,
                                                  start_date__lt=date.today())
                }

                if 'status' in filters and len(filters["status"]) > 0:
                    not_joined = Project.objects.none()
                    if 'not_joined' in filters["status"]:
                        not_joined = projects.filter(statuses__status='on_boarded', statuses__is_current=True,
                                                     start_date__lt=date.today())
                    projects = projects.filter(statuses__status__in=filters['status'], statuses__is_current=True)
                    projects = (projects | not_joined).distinct('id')
            else:
                if filter_by_lead == 'w2':
                    projects = projects.filter(submission__lead__is_w2=True)

                if filter_by_time:
                    projects = get_time_filter(projects, filter_by_time)

                projects = projects.order_by('id').distinct('id')
                data = {
                    "total": projects,
                    "new": projects.filter(statuses__status='new', statuses__is_current=True),
                    "joined": projects.filter(statuses__status='joined', statuses__is_current=True),
                    "received": projects.filter(statuses__status='received', statuses__is_current=True),
                    "on_boarded": projects.filter(statuses__status='on_boarded', statuses__is_current=True),
                    "not_joined": projects.filter(statuses__status='on_boarded', statuses__is_current=True,
                                                  start_date__lt=date.today())
                }

                if filter_by_status:
                    projects = data[filter_by_status]

            data_count = {
                'new': data["new"].count(),
                'total': data["total"].count(),
                'joined': data["joined"].count(),
                'received': data["received"].count(),
                'on_boarded': data["on_boarded"].count(),
                'not_joined': data["not_joined"].count(),
            }

            if version == 'v2' and filter_json:
                # count of project by status
                if sort_by in ['created', 'modified']:
                    order_by = f"-{sort_by}"
                elif sort_by == 'consultant':
                    order_by = '-submission__consultant_marketing__consultant__name'
                else:
                    order_by = '-modified'

                projects = Project.objects.filter(id__in=projects.values('id')).order_by(order_by)
            serializer = self.serializer_class(projects[first:last], many=True)
            return Response({"counts": data_count, "data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        sub_id = request.data.get('submission')
        try:
            sub = get_object_or_404(Submission, id=sub_id, created_by=request.user)
            if hasattr(sub, 'project'):
                return Response({"message": "Project already exist"}, status=406)

            # Adding Remote consultant
            remote_consultant = create_remote_consultant(request)
            if remote_consultant:
                consultant = remote_consultant
            else:
                consultant = sub.consultant

            serializer = self.serializer_class(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                project = Project.objects.get(id=serializer.data['id'])
                ProjectStatus.objects.create(status='new', project=project, is_current=True)

                project.city = sub.lead.city
                project.consultant = consultant
                project.rate = project.submission.rate
                project.employer = project.submission.employer
                project.is_remote = request.data.get('is_remote', False)
                project.save()

                sub.status = 'project'
                sub.save()

                message, exception_msg = self.send_support_offer_mail(project, self.fetch_scrum_masters(request))
                serializer = self.serializer_class(project)
                return Response({
                    "message": message,
                    "data": serializer.data,
                    "exception": exception_msg,
                }, status=201)
            write_exception(serializer.errors, request)
            return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            err = None
            new_status = request.data.get('status', None)
            project = get_object_or_404(Project, id=project_id)
            prev_status_obj = project.statuses.get(is_current=True)

            util = ProjectUtil(project)

            all_status, cancellation_status, termination_status = util.statuses

            if new_status not in all_status:
                return Response({"message": 'Project status does not exist'}, status=400)

            project.city = request.data.get('city', project.city)
            project.rate = request.data.get('rate', project.rate)
            project.duration = request.data.get('duration', project.duration)
            project.end_date = request.data.get('end_date', project.end_date)
            project.feedback = request.data.get('feedback', project.feedback)
            project.employer = request.data.get('employer', project.employer)
            project.start_date = request.data.get('start_date', project.start_date)
            project.payment_term = request.data.get('payment_term', project.payment_term)
            project.client_address = request.data.get('client_address', project.client_address)
            project.vendor_address = request.data.get('vendor_address', project.vendor_address)
            project.invoicing_period = request.data.get('invoicing_period', project.invoicing_period)
            project.reporting_details = request.data.get('reporting_details', project.reporting_details)

            consultant = create_remote_consultant(request)
            if consultant:
                project.consultant = consultant
            project.is_remote = request.data.get('is_remote', False)
            project.save()

            prev_statuses = list(project.statuses.all().values_list('status', flat=True))
            if new_status not in prev_statuses:
                scrum_masters = self.fetch_scrum_masters(request)

                project_status_obj, status_created = ProjectStatus.objects.get_or_create(
                    is_current=True,
                    project=project,
                    status=new_status.lower(),
                )
                if status_created:
                    prev_status_obj.is_current = False
                    prev_status_obj.save()

                marketing = project.submission.consultant_marketing

                # PO Received
                if new_status == 'received' and not project.is_msg_sent:
                    # Offer received message
                    util.send_receive_notification(request.user)
                    project.is_msg_sent = True
                    project.save()

                # Project Joined
                elif new_status == 'joined':
                    project.consultant.status = 'on_project'
                    project.consultant.save()
                    if marketing.status == 'open':
                        marketing.end = date.today()
                        marketing.status = 'close'
                        marketing.save()

                    # Creating first week Timesheet on project status change to joined
                    util.create_timesheet()

                    # Setting password for User (consultant)
                    password, new_user = set_consultant_password(project.consultant)
                    resp, err = self.consultant_mail_on_joining(project, password, new_user)

                    util.send_join_notification(request.user)

                # Project Cancelled
                elif prev_status_obj.status not in cancellation_status and new_status in cancellation_status:
                    marketing.status = 'open'
                    marketing.save()
                    project.support.update(end=datetime.now())
                    resp, err = self.po_end_mail(project, scrum_masters, 'PO Cancelled')
                    util.send_cancellation_notification(request.user)

                # Project Terminated
                elif prev_status_obj.status not in termination_status and new_status in termination_status:
                    project.consultant.status = 'on_bench'
                    project.consultant.save()
                    project.support.update(end=datetime.now())
                    resp, err = self.po_end_mail(project, scrum_masters, 'PO Terminated')
                    po_status = project_status_obj.get_status_display()
                    util.send_termination_notification(po_status, request.user)

                # Project Completed
                elif prev_status_obj.status != 'complete' and new_status == "complete":
                    project.consultant.status = 'on_bench'
                    project.consultant.save()
                    project.support.update(end=datetime.now())
                    resp, err = self.po_end_mail(project, scrum_masters, 'project completed')
                    util.send_completion_notification(request.user)

            serializer = self.serializer_class(project)

            return Response({"data": serializer.data, "error": err, "message": "Project updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path="mail_to_onboard")
    def mail_to_onboard(self, request):
        try:
            project_id = request.query_params.get('project_id', None)
            if project_id:

                project = get_object_or_404(Project, id=project_id)
                result = get_attachment_status(project)
                if not result["status"]:
                    return Response({"message": "Complete all details"}, status=400)

                prev_status = project.statuses.filter(is_current=True).first()
                po_type = 'created'
                if prev_status.status == 'on_boarded':
                    po_type = 'updated'

                path = []

                for i in project.attachments.filter(
                        attachment_type__in=['work_order_signed', 'work_order_msa_signed', 'msa_signed']):
                    try:
                        path.append(download_s3_object(i.attachment_file.name))
                    except Exception as error:
                        write_exception(error, request)

                res, error = 'development server', 'development server'
                if os.environ.get('ENV', 'local') == 'prod':
                    res, error = self.po_mail(project, path, self.fetch_scrum_masters(request), po_type)
                delete_temp_file(path)
                if not error == 'error':
                    project.submission.consultant_marketing.status = 'close'
                    project.submission.consultant_marketing.end = project.start_date
                    project.submission.consultant_marketing.save()
                    if prev_status.status == 'received' or prev_status.status == 'new':
                        new_status, created = ProjectStatus.objects.get_or_create(
                            project=project,
                            is_current=True,
                            status='on_boarded',
                        )
                        if created:
                            prev_status.is_current = False
                            prev_status.save()
                    return Response({"message": "On-boarding mail sent", "error": res}, status=200)
                return Response({"data": str(res)}, status=400)
            else:
                return Response({"message": "Invalid Id"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="send_support_mail")
    def send_support_and_offer_mail(self, request, *args, **kwargs):
        try:
            project_id = kwargs.get('pk')
            project = get_object_or_404(Project, id=project_id)

            message, exception_msg = self.send_support_offer_mail(project, self.fetch_scrum_masters(request))

            if exception_msg != 'Mail sent':
                return Response({
                    "exception": exception_msg,
                    "message": "Unable to send Support or Offer mail"
                }, status=400)

            return Response({"data": exception_msg, "message": "Support and Offer mail sent"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            fields, group = [], None
            status = project.statuses.filter(is_current=True).first().status
            if project.submission.created_by.id == request.user.id:
                group = ObjectGroup.objects.filter(name='owner', model='project', status=status)
            if request.user.role.name == 'finance':
                group = ObjectGroup.objects.filter(name='finance', model='project', status=status)
            if group:
                fields = group.first().fields.all().values_list('name', flat=True)
            return Response({"data": fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project_support/
class ProjectSupportViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = ProjectSupport.objects.all()
    serializer_class = ProjectSupportSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.query_params.get('project_id'))
            serializer = ProjectSupportSerializer(project.support.all().order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.data['project_id'])
            users = request.data.get('support', [])
            support_names = []
            for user in users:
                support = get_object_or_404(User, id=user['id'])
                support_names.append(support.employee_name)
                if not user['start']:
                    return Response({"message": "Start date can not be empty"}, status=400)
                project_support = ProjectSupport.objects.create(
                    project=project,
                    support=support,
                    start=user['start'],
                    is_primary=user['primary'],
                )
                SupportStatus.objects.create(
                    is_current=True,
                    support=project_support,
                    change_date=user['start'],
                    frequency=user['frequency'],
                )
            # notification
            user_list = []
            aux_verb = "is"
            if len(support_names) > 1:
                aux_verb = "are"
            consultant = project.submission.consultant
            names = ", ".join(name for name in support_names)
            pocs = consultant.pocs.all()
            for data in pocs:
                user_list.append(data.poc)
            user_list.append(project.submission.created_by)
            title = f"""{names} {aux_verb} assigned as support to {consultant.name}'s project of 
                {project.submission.client}"""
            notification_data = {
                'title': title,
                'target_id': None,
                'category': 'info',
                'description': title,
                'parent_id': project.id,
                'parent_type': 'project',
                'sender_user_type': 'user',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
                'target_type': 'projectsupport',
            }
            create_notification(user_list, notification_data)
            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'submission',
                    'sub_target': 'support',
                    'timestamp': str(datetime.now()),
                    'target_id': project.submission.id,
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)
            serializer = ProjectSupportSerializer(project.support.all(), many=True)
            return Response({"data": serializer.data, "message": "Support is added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            support = get_object_or_404(ProjectSupport, id=kwargs.get('pk'))
            project = support.project
            all_support = project.support.filter(end=None)
            primary_support = [user for user in all_support if user.is_primary is True]

            if len(primary_support) == 1 and primary_support[0] == support and request.data.get('is_primary') is False:
                return Response({"message": 'At least one support should be primary'}, status=400)

            support.is_primary = request.data.get('is_primary')
            support.save()
            start = request.data.get('start')
            new_freq = request.data.get('frequency')
            prev = support.statuses.filter(is_current=True)
            if prev.first() and prev.first().frequency != new_freq:
                prev.update(is_current=False)
                SupportStatus.objects.create(
                    is_current=True,
                    support=support,
                    change_date=start,
                    frequency=new_freq,
                )
            elif not prev.first():
                SupportStatus.objects.create(
                    is_current=True,
                    support=support,
                    change_date=start,
                    frequency=new_freq,
                )
            serializer = ProjectSupportSerializer(support)
            return Response({"data": serializer.data, "message": "Support is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path="remove")
    def remove_support(self, request, *args, **kwargs):
        try:
            support = get_object_or_404(ProjectSupport, id=kwargs.get('pk'))
            support.end = request.data.get('end')
            support.feedback = request.data.get('feedback', None)
            support.save()
            serializer = ProjectSupportSerializer(support)
            return Response({"data": serializer.data, "message": "Support is removed"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project_order/
class ProjectOrderViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = ProjectOrder.objects.all()
    serializer_class = ProjectOrderSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.query_params.get('project_id'))
            serializer = ProjectOrderSerializer(project.order.all().order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.data.get('project_id'))
            effective_date = request.data.get('effective_date')
            desc = ""
            if request.data.get('field') == 'rate':
                project.rate = request.data.get('value')
                desc = f"Project {project.submission.consultant.name} :: {project.submission.client} rate changed to " \
                       f"{request.data.get('value')} by {request.user.employee_name}"

            elif request.data.get('field') == 'employer':
                project.employer = request.data.get('value')
                desc = f"Project {project.submission.consultant.name} :: {project.submission.client} employer " \
                       f"changed to {request.data.get('value')} by {request.user.employee_name}"

            elif request.data.get('field') == 'end_date':
                effective_date = project.end_date
                project.end_date = request.data.get('value')
                desc = f"Project {project.submission.consultant.name} :: {project.submission.client} extended to " \
                       f"{request.data.get('value')} by {request.user.employee_name}"

            order = ProjectOrder.objects.create(
                project=project,
                created_by=request.user,
                effective_date=effective_date,
                value=request.data.get('value'),
                field=request.data.get('field'),
            )
            project.save()

            if request.FILES.getlist('file'):
                attachments = project.attachments.all()
                for attachment in attachments:
                    attachment.is_active = False
                    attachment.save()

                for file in request.FILES.getlist('file'):
                    file_data = {
                        "file": file,
                        "model": "project",
                        "object_id": project.id,
                        "creator": request.user,
                        "type": request.data.get('file_type'),
                    }
                    create_attachment(file_data)
            create_activity(order.id, 'projectorder', request.user, desc, 'created')
            serializer = self.serializer_class(project.order.all(), many=True)
            return Response({"data": serializer.data, "message": "Project order created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            order = get_object_or_404(ProjectOrder, id=kwargs.get('pk'))
            prev_value = order.value
            serializer = ProjectOrderSerializer(order, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                if order.field == 'rate' and prev_value == str(int(order.project.rate)):
                    order.project.rate = request.data.get('value')
                    order.project.save()

                elif order.field == 'employer' and prev_value == order.project.employer:
                    order.project.employer = request.data.get('value')
                    order.project.save()

                elif order.field == 'end_date' and prev_value == str(order.project.end_date):
                    order.project.end_date = request.data.get('value')
                    order.project.save()

                desc = f"Project Order details updated by {request.user.employee_name}"
                create_activity(order.id, 'projectorder', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Project order updated"}, status=202)
            return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /eng_project/
class EngineeringProjectsViewSets(viewsets.GenericViewSet, ListModelMixin):
    authentication_classes = ()
    permission_classes = (HasAPIKey,)
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def list(self, request, *args, **kwargs):
        try:
            end = request.query_params.get("end", None)
            start = request.query_params.get("start", None)
            if start and end:
                projects = Project.objects.select_related('submission').filter(modified__range=[start, end])
            else:
                projects = Project.objects.select_related('submission').all()

            recruiter = ConsultantPOC.objects.filter(
                consultant=OuterRef("consultant_id"), end=None, poc_type='recruiter')

            relation = ConsultantPOC.objects.filter(
                consultant=OuterRef("consultant_id"), end=None, poc_type='relation')

            data = projects.annotate(
                location=F('city'),
                status=F('statuses__status'),
                client=F('submission__client'),
                job_desc=F('submission__lead__job_desc'),
                job_title=F('submission__lead__job_title'),
                marketer_email=F('submission__created_by__email'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
                relation=Subquery(relation.values('poc__employee_name')[:1]),
                recruiter=Subquery(recruiter.values('poc__employee_name')[:1]),
            ).values(
                'id', 'client', 'consultant__name', 'consultant__email', 'status', 'feedback', 'client', 'start_date',
                'consultant__phone_no', 'created', 'modified', 'recruiter', 'relation', 'marketer_name', 'job_title',
                'marketer_email', 'vendor', 'location', 'end_date', 'job_desc', 'employer')

            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)


# Route - /finance/
class FinanceTimeSheetViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = FinanceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.query_params.get('query', None)
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', date.today())

        try:
            projects = Project.objects.filter(
                Q(statuses__is_current=True, consultant_id=kwargs.get('pk', None)) & (
                        Q(statuses__status__istartswith='terminated') |
                        Q(statuses__status='complete') |
                        Q(statuses__status='joined')
                )
            )
            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )
            if projects:
                ids = list(projects.values_list('id', flat=True))
                if start:
                    queryset = TimeSheet.objects.filter(
                        project__in=ids, start__range=[start, end]
                    ).exclude(status='draft')
                else:
                    queryset = TimeSheet.objects.filter(project__in=ids).exclude(status='draft')

                total = queryset.count()
                serializer = self.serializer_class(queryset[first:last], many=True)
                return Response({"data": serializer.data, 'total': total}, status=200)
            return Response({"message": "No Project Found"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.query_params.get('query', None)
        consultant_id = request.query_params.get('consultant', None)
        consultant_name = request.query_params.get('consultant_name', None)

        try:

            project_status = ['joined', 'terminated-resigned', 'terminated', 'terminated-resigned_location_issue',
                              'terminated-resigned_location_issue', 'terminated-resigned_full_time_offer',
                              'terminated-resigned_technology_issue', 'terminated-fired_budget_issue',
                              'terminated-fired_performance_issue', 'terminated-fired_security_issue', 'complete']

            if consultant_id:
                consultants = Consultant.objects.filter(id=consultant_id).exclude(status='archived')
            elif consultant_name:
                consultants = Consultant.objects.filter(name__istartswith=consultant_name).exclude(status='archived')
            else:
                consultant_ids = Project.objects.filter(
                    statuses__status__in=project_status, statuses__is_current=True
                ).values_list('consultant', flat=True)
                consultants = Consultant.objects.filter(
                    id__in=list(consultant_ids),
                    projects__timesheets__is_active=True,
                    projects__timesheets__status='submitted',
                ).exclude(status='archived').order_by('id').distinct('id')

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
                    timesheet.is_active = False
                    timesheet.save()

                    timesheet = TimeSheet.objects.create(
                        hours=0,
                        status='rejected',
                        end=timesheet.end,
                        start=timesheet.start,
                        remark=timesheet.remark,
                        project=timesheet.project,
                    )
                    recipient_content_type = ContentType.objects.get(model='consultant')
                    sender_content_type = ContentType.objects.get(model='user')
                    target_content_type = ContentType.objects.get(model='timesheet')

                    if timesheet.remark or len(timesheet.remark) != 0:
                        title = f"Timesheet rejected for week end {str(timesheet.end)} for client " \
                                f"{timesheet.project.submission.client} \n Remark: {timesheet.remark}"
                    else:
                        title = f"Timesheet rejected for week end {str(timesheet.end)} for client " \
                                f"{timesheet.project.submission.client}"

                    Notification.objects.create(
                        title=title,
                        description=title,
                        category="rejected",
                        target_object_id=timesheet.id,
                        sender_object_id=request.user.id,
                        sender_content_type=sender_content_type,
                        target_content_type=target_content_type,
                        recipient_content_type=recipient_content_type,
                        recipient_object_id=timesheet.project.consultant.id,
                    )

                    # Push Notification
                    message_body = {
                        "body": title,
                        "title": title,
                        "category": "rejected",
                        "show_in_foreground": True,
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "data": {
                            'is_read': False,
                            'is_deleted': False,
                            'target': 'timesheet',
                            'target_id': timesheet.id,
                            'timestamp': str(timezone.now()),
                        },
                    }
                    object_ids = timesheet.project.consultant.consultant_token.all().values_list('key', flat=True)
                    registration_ids = list(
                        FCMDevice.objects.filter(
                            object_id__in=list(object_ids), content_type__model='consultanttoken'
                        ).values_list('device_id', flat=True))
                    push_notification_consultant(registration_ids, message_body)
                serializer = self.serializer_class(timesheet)
                return Response({"data": serializer.data, "message": "Timesheet is updated"}, status=202)
            return Response({"message": "You don't have access"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=["get"], detail=True, url_name="from_notification")
    def from_notification(self, request, *args, **kwargs):
        try:
            queryset = TimeSheet.objects.filter(id=kwargs.get('pk'))
            serializer = self.serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
