import os
import json
import inspect
from datetime import datetime, date, timedelta

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
from consultant.utils import send_notification_for_user
from consultant.models import ConsultantPOC, Consultant
from notification.models import Notification, FCMDevice
from attachment.views import download_s3_object, delete_temp_file
from utils_app.mailing import send_email_attachment_multiple, send_email
from notification.utils import create_notification, push_notification, push_notification_consultant
from project.models import Project, ProjectStatus, ProjectOrder, TimeSheet, ProjectSupport, SupportStatus
from log1.utils import get_time_filter, post_msg_using_webhook, password_generator, get_page_limits, write_exception
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
            res = send_email(mail_data, config.RELATIONS)
            return res, "ok"
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return error, "error"

    def send_offer_received_mail(self, project, submission, scrum_masters):
        try:
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
                'subject': f'Offer Received of {consultant.name} :: {submission.client} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/offer.html',
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
            res = None
            if os.environ.get("ENV") == 'prod':
                res = send_email(mail_data, submission.created_by.email)
            return res, "ok"
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return error, "error"

    def support_mail(self, project, submission, scrum_masters):
        try:
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
                'to': [config.ENGINEERING],
                'cc': cc,
                'bcc': [],
                'subject': f'Support Initiation for {consultant.name} {submission.client} {submission.lead.city}',
                'template': '../templates/support.html',
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
                'attachments': path
            }
            res = None
            if os.environ.get("ENV") == 'prod':
                res = send_email_attachment_multiple(mail_data, submission.created_by.email)

            delete_temp_file(path)
            return res, "ok"
        except Exception as error:
            return error, "error"

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
                'subject': f'On Boarding of {consultant.name} :: {project.employer} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/po.html',
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
                'attachments': path
            }
            res = send_email_attachment_multiple(mail_data, marketer.email)
            return res, "ok"
        except Exception as error:
            write_exception(message=f"Offer mail error for {marketer.email}: {error}",
                            class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return error, "error"

    def po_termination_or_cancellation_mail(self, project, scrum_master_email, po_type):
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
                'subject': f'{po_type} of {consultant.name} :: {project.employer} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/po_termination.html',
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
            res1 = send_email(mail_data, marketer.email)
            to_engineering = [config.ENGINEERING]
            mail_data_eng = {
                'to': to_engineering,
                'cc': [],
                'bcc': [],
                'subject': f'{po_type} of {consultant.name} :: '
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/po_termination_engineering.html',
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
            res2 = send_email(mail_data_eng, marketer.email)
            return f"Res1: {res1} and res2: {res2}", "ok"
        except Exception as error:
            write_exception(message="Offer mail error for {}".format(marketer.email) + str(error),
                            class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
                order_by = '-created'
                if sort_by:
                    field_name, order = sort_by.split("_") if len(sort_by.split("_")) > 1 else (sort_by, "asc")
                    if field_name == 'created':
                        order_by = "created" if order == "asc" else "-created"
                    elif field_name == 'modified':
                        order_by = "modified" if order == "asc" else "-modified"
                    elif field_name == 'consultant':
                        order_by = "submission__consultant_marketing__consultant__name" if order == "asc" \
                            else "-submission__consultant_marketing__consultant__name"

                projects = Project.objects.filter(id__in=projects.values('id')).order_by(order_by)
            serializer = self.serializer_class(projects[first:last], many=True)
            return Response({"counts": data_count, "data": serializer.data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        sub_id = request.data.get('submission')
        try:
            sub = get_object_or_404(Submission, id=sub_id, created_by=request.user)
            if hasattr(sub, 'project'):
                return Response({"message": "Project already exist"}, status=406)

            is_remote = request.data.get('is_remote', False)
            remote_consultant_id = request.data.get('remote_consultant_id', None)
            if remote_consultant_id:
                if request.data.get('remote_consultant_type', None) == 'user':
                    user = User.objects.get(id=remote_consultant_id)
                    consultant, created = Consultant.objects.get_or_create(
                        email=user.email,
                        gender=user.gender,
                        name=user.employee_name,
                    )
                    consultant.remote_only = True
                    consultant.save()
                else:
                    consultant = get_object_or_404(Consultant, id=remote_consultant_id)
                    consultant.remote_only = True
                    consultant.save()
            else:
                consultant = sub.consultant

            serializer = self.serializer_class(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                project = Project.objects.get(id=serializer.data['id'])
                ProjectStatus.objects.create(
                    status='new',
                    project=project,
                    is_current=True,
                )

                sub.status = 'project'
                sub.save()

                project.city = sub.lead.city
                project.is_remote = is_remote
                project.consultant = consultant
                project.rate = project.submission.rate
                project.employer = project.submission.employer
                project.save()

                scrum_masters = list(User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'],
                                                         is_active=True).values_list('email', flat=True))

                support_mail_res = "Development Server"
                offer_mail_res = "Development Server"

                if os.environ.get('ENV', 'local') == 'prod':
                    support_mail_res, support_mail_error = self.support_mail(project, sub, scrum_masters)
                    offer_mail_res, offer_mail_error = self.send_offer_received_mail(project, sub, scrum_masters)
                    if support_mail_error == 'error' or offer_mail_error == 'error':
                        write_exception(message=f"Support: {support_mail_res}, Offer: {offer_mail_res}",
                                        class_name=self.get_classname(), function_name=inspect.stack()[0][3])
                        return Response({
                            "support_mail_error": str(support_mail_res),
                            "message": "Unable to send Support/Offer mail",
                            "offer_mail_error": offer_mail_error}, status=400)

                serializer = self.serializer_class(project)
                return Response({
                    "data": serializer.data,
                    "message": "Project created",
                    "offer_mail": str(offer_mail_res),
                    "support_mail": str(support_mail_res),
                }, status=201)
            write_exception(message=serializer.errors, class_name=self.get_classname(),
                            function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            err = None
            new_status = request.data.get('status', None)
            project = get_object_or_404(Project, id=project_id)
            prev_status_obj = project.statuses.get(is_current=True)

            cancellation_status = ['cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled',
                                   'cancelled-contract_conflicts', 'cancelled-candidate_denied',
                                   'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
                                   'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location']
            termination_status = ['terminated', 'terminated-resigned', 'terminated-fired',
                                  'terminated-resigned_rate_issue', 'terminated-resigned_technology_issue',
                                  'terminated-fired_budget_issue', 'terminated-fired_security_issue',
                                  'terminated-resigned_location_issue', 'terminated-fired_performance_issue',
                                  'terminated-resigned_full_time_offer']

            all_status = ['new', 'other', 'joined', 'received', 'signed', 'extended', 'on_boarded', 'complete']
            all_status = all_status + cancellation_status + termination_status

            if new_status not in all_status:
                return Response({"message": 'Project status does not exist'}, status=400)

            data = {
                "city": request.data.get('city', project.city),
                "rate": request.data.get('rate', project.rate),
                "duration": request.data.get('duration', project.duration),
                "end_date": request.data.get('end_date', project.end_date),
                "feedback": request.data.get('feedback', project.feedback),
                "employer": request.data.get('employer', project.employer),
                "start_date": request.data.get('start_date', project.start_date),
                "payment_term": request.data.get('payment_term', project.payment_term),
                "client_address": request.data.get('client_address', project.client_address),
                "vendor_address": request.data.get('vendor_address', project.vendor_address),
                "invoicing_period": request.data.get('invoicing_period', project.invoicing_period),
                "reporting_details": request.data.get('reporting_details', project.reporting_details),
                "remote_consultant_id": request.data.get('remote_consultant_id', None),
                "remote_consultant_type": request.data.get('remote_consultant_type', None),

            }
            project.city = data["city"]
            project.rate = data["rate"]
            project.duration = data["duration"]
            project.end_date = data["end_date"]
            project.feedback = data["feedback"]
            project.employer = data["employer"]
            project.start_date = data["start_date"]
            project.payment_term = data["payment_term"]
            project.client_address = data["client_address"]
            project.vendor_address = data["vendor_address"]
            project.invoicing_period = data["invoicing_period"]
            project.reporting_details = data["reporting_details"]

            if data["remote_consultant_id"]:
                if data['remote_consultant_type'] == 'user':
                    user = User.objects.get(id=request.data["remote_consultant_id"])
                    consultant, created = Consultant.objects.get_or_create(
                        email=user.email,
                        gender=user.gender,
                        name=user.employee_name,
                    )
                    consultant.remote_only = True
                    consultant.save()
                else:
                    consultant = get_object_or_404(Consultant, id=request.data["remote_consultant_id"])
                project.consultant = consultant

            is_remote = request.data.get('is_remote', None)
            project.is_remote = is_remote
            project.save()

            # Emoji for Mattermost update
            if project.consultant.recruiter:
                recruiter_gender_emoji = '&#128103;' if project.consultant.recruiter.gender == 'female' else '&#129490;'
                recruiter = project.consultant.recruiter.employee_name
            else:
                recruiter_gender_emoji = '&#129490; '
                recruiter = "NA"

            client_emoji = '&#127913;'
            role_emoji = '&#128074;'
            employer_emoji = '&#x1F4BC;'
            marketer_gender_emoji = '&#128105;' if project.submission.created_by.gender == 'female' else '&#128104;'
            consultant_gender_emoji = '&#128105;' if project.consultant.gender == 'female' else '&#128104;'

            # For Status Change
            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            project_end_date = None
            if project.end_date:
                project_end_date = datetime.strptime(str(project.end_date), '%Y-%m-%d').strftime('%m/%d/%Y')

            prev_statuses = list(project.statuses.all().values_list('status', flat=True))
            if new_status not in prev_statuses:
                p_status, p_s_created = ProjectStatus.objects.get_or_create(
                    is_current=True,
                    project=project,
                    status=new_status.lower(),
                )
                if p_s_created:
                    prev_status_obj.is_current = False
                    prev_status_obj.save()

                # If status is Joined
                if new_status.startswith('cancelled'):
                    project.submission.consultant_marketing.status = 'open'
                    project.submission.consultant_marketing.save()
                    title = f"Project Cancelled :: {project.consultant.name} :: {project.submission.client}"
                    send_notification_for_user(project.consultant, request.user, title, 'project')

                if new_status == 'joined':
                    project.consultant.status = 'on_project'
                    project.consultant.save()
                    project.submission.consultant_marketing.status = 'close'
                    project.submission.consultant_marketing.end = date.today()
                    project.submission.consultant_marketing.save()

                    day_one = datetime.today().replace(day=1, hour=0, minute=0)
                    total_joined_count = Project.objects.filter(
                        statuses__status='joined',
                        statuses__created__gte=day_one,
                    ).count()

                    team_joined_count = Project.objects.filter(
                        statuses__status='joined',
                        statuses__created__gte=day_one,
                        employer__iexact=project.employer,
                    ).count()
                    if project.is_remote or project.submission.lead.is_w2:
                        con_str = f"**Remote Project** <br>"
                        con_str += f"{consultant_gender_emoji} Consultant Joined: **{project.consultant.name.strip()}** <br>"
                        con_str += f"{consultant_gender_emoji} Submitted On: **{project.consultant.name.strip()}** "
                    else:
                        con_str = f"{consultant_gender_emoji} Consultant :  **{project.consultant.name.strip()}** "

                    # Sending message on Mattermost on joined status
                    data = {
                        "title": "Project Joined  &#129304;&#128516;&#129304;",
                        "text": f"""{con_str}<br>
                    {marketer_gender_emoji} Marketer :  {project.marketer_name} <br>
                    {recruiter_gender_emoji} Recruiter :  {recruiter} <br>
                    {employer_emoji} Employer :  {project.employer}<br>
                    {employer_emoji} Team :  {project.submission.created_by.team.name}<br>
                    🇺🇸 Location :  {project.city}<br>
                    {client_emoji} Client :  {project.submission.client}<br>
                    {role_emoji} Role :  {project.submission.lead.job_title}<br>
                    &#128221; Joining Date :  {project_start_date}<br><br>
                    Project Joined count of {project.employer} for this month - {team_joined_count}<br>
                    Total Project Joined count of this month - {total_joined_count}"""
                    }
                    post_msg_using_webhook(config.joined_url, data)

                    title = f" Project Joined :: {project.consultant.name} :: {project.submission.client}"
                    send_notification_for_user(project.consultant, request.user, title, 'project')

                    consultant = project.consultant

                    # Creating first week Timesheet on project status change to joined
                    start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d')
                    week_day = start_date.weekday()
                    if week_day == 6:
                        end_date = start_date + timedelta(days=6)
                    else:
                        end_date = start_date + timedelta(days=5 - week_day)

                    for i in range(2):
                        TimeSheet.objects.get_or_create(
                            hours=0,
                            end=end_date,
                            status='draft',
                            project=project,
                            start=start_date,
                        )
                        start_date = end_date + timedelta(days=1)
                        end_date = end_date + timedelta(days=7)

                    if os.environ.get('ENV', 'local') == 'prod':
                        if not consultant.is_active:
                            password = password_generator(password_length=10, strength=3)
                            consultant.set_password(password)
                            consultant.is_active = True
                            consultant.save()

                            resp, err = self.consultant_mail_on_joining(project, password, True)
                        else:
                            resp, err = self.consultant_mail_on_joining(project, "password", False)

                # Discord message for PO , Status Received
                if new_status == 'received' and not project.is_msg_sent:
                    day_one = datetime.today().replace(day=1, hour=0, minute=0)
                    total_offer_count = Project.objects.filter(
                        statuses__status='received',
                        statuses__created__gte=day_one,
                    ).count()

                    team_offer_count = Project.objects.filter(
                        statuses__status='received',
                        statuses__created__gte=day_one,
                        employer__iexact=project.employer,
                    ).count()
                    interviews = project.submission.screening.exclude(status='cancelled')
                    ctb_gender = interviews.last().supervisor.gender
                    supervisors = "\n".join(
                        [f"<li>Round {interview.round} - {interview.supervisor.employee_name}</li>"
                         for interview in interviews if interview.supervisor])
                    ctb_gender_emoji = '&#128587;' if ctb_gender == 'female' else '&#129490;'
                    if project.is_remote and project.submission.lead.is_w2:
                        con_str = f"**Remote Project** <br>"
                        con_str += f"{consultant_gender_emoji} Consultant Joined: **{project.consultant.name}** <br>"
                        con_str += f"{consultant_gender_emoji} Submitted On: **{project.submission.consultant.name}** "
                    else:
                        con_str = f"{consultant_gender_emoji} Consultant :  **{project.consultant.name}**"
                    # Sending message on Messaging Tool
                    data = {
                        "title": "Offer  &#129304;&#128516;&#129304;",
                        "text": f"""{con_str} <br>
                        {marketer_gender_emoji} Marketer :  {project.marketer_name} <br>
                        {recruiter_gender_emoji} Recruiter :  {recruiter} <br>
                        {employer_emoji} Employer :  {project.employer}<br>
                        {employer_emoji} Team :  {project.submission.created_by.team.name}<br>
                        {ctb_gender_emoji} CTB :  <ul>{supervisors}</ul> 🇺🇸 Location :  {project.city}
                        <br> {client_emoji} Client :  {project.submission.client}
                        <br> {role_emoji} Role :  {project.submission.lead.job_title}
                        <br> &#128221; Start Date :  {project_start_date}
                        <br> <br> Offer count of {project.employer} for this month - {team_offer_count}
                        <br> Total offer count of this month - {total_offer_count}"""
                    }
                    post_msg_using_webhook(config.offer_url, data)
                    project.is_msg_sent = True
                    project.save()
                    title = f" Project Received :: {project.consultant.name} :: {project.submission.client}"
                    send_notification_for_user(project.consultant, request.user, title, 'project')

                # Mail for Cancellation or Termination of Project

                if os.environ.get('ENV', 'local') == 'prod':
                    scrum_masters = list(User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy']
                                                             ).values_list('email', flat=True))

                    if prev_status_obj.status not in termination_status and new_status in termination_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_masters, 'PO Termination')
                        project.consultant.status = 'on_bench'
                        project.consultant.save()
                        project.support.update(end=datetime.now())

                        text = f"""{consultant_gender_emoji} Consultant :  **{project.consultant.name}** <br>
                        {marketer_gender_emoji} Marketer :  {project.marketer_name} <br>
                        {recruiter_gender_emoji} Recruiter :  {recruiter} <br>
                        {employer_emoji} Employer :  {project.employer} <br>
                        {employer_emoji} Team :  {project.submission.created_by.team.name} <br>
                        {client_emoji} Client :  {project.submission.client} <br>
                        {role_emoji} Role :  {project.submission.lead.job_title} <br>
                        &#128221; Start Date :  {project_start_date} <br>
                        &#128221; End Date :  {project_end_date} <br>
                        &#10060; Status :  {str(p_status.get_status_display())} <br>"""

                        text += " **Reason:** " + " " + project.feedback if project.feedback else "None"

                        data = {
                            "title": "Offer Termination Feedback",
                            "text": text
                        }
                        post_msg_using_webhook(config.project_termination_url, data)
                        title = f"Project Terminated :: {project.consultant.name} :: {project.submission.client}"
                        send_notification_for_user(project.consultant, request.user, title, 'project')

                    elif prev_status_obj.status not in cancellation_status and new_status in cancellation_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_masters, 'PO Cancelled')

                        text = f"""{consultant_gender_emoji} Consultant :  **{project.consultant.name}** <br>
                        {marketer_gender_emoji} Marketer :  {project.marketer_name} <br>
                        {recruiter_gender_emoji} Recruiter :  {recruiter} <br>
                        {employer_emoji} Employer :  {project.employer}<br>
                        {employer_emoji} Team :  {project.submission.created_by.team.name}<br>
                         🇺🇸 Location :  {project.city}<br>
                        {client_emoji} Client :  {project.submission.client}<br>
                        {role_emoji} Role :  {project.submission.lead.job_title}<br>
                        &#128221; Joining Date :  {project_start_date}<br>"""

                        text += " **Reason:** " + project.feedback if project.feedback else "None"

                        data = {
                            "title": "Offer Cancellation Feedback ",
                            "text": text
                        }
                        post_msg_using_webhook(config.offer_failure_url, data)

                    elif prev_status_obj.status != 'complete' and new_status == "complete":
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_masters, 'Project completed')
                        project.consultant.status = 'on_bench'
                        project.consultant.save()
                        title = f" Project Completed :: {project.consultant.name} :: {project.submission.client}"
                        send_notification_for_user(project.consultant, request.user, title, 'project')

            serializer = self.serializer_class(project)

            return Response({"data": serializer.data, "error": err, "message": "Project updated"}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
                scrum_masters = list(User.objects.filter(
                    team=request.user.team, role__name__in=['admin', 'proxy']
                ).values_list('email', flat=True))

                for i in project.attachments.filter(
                        attachment_type__in=['work_order_signed', 'work_order_msa_signed', 'msa_signed']):
                    try:
                        path.append(download_s3_object(i.attachment_file.name))
                    except Exception as error:
                        write_exception(message=error, class_name=self.get_classname(),
                                        function_name=inspect.stack()[0][3])

                res, error = 'development server', 'development server'
                if os.environ.get('ENV', 'local') == 'prod':
                    res, error = self.po_mail(project, path, scrum_masters, po_type)
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="send_support_mail")
    def send_support_mail(self, request, *args, **kwargs):
        try:
            project_id = kwargs.get('pk')
            project = get_object_or_404(Project, id=project_id)

            queryset = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'], is_active=True)
            scrum_masters = [user.email for user in queryset]

            support_mail_res, support_mail_error = self.support_mail(project, project.submission, scrum_masters)
            offer_mail_res, offer_mail_error = self.send_offer_received_mail(project, project.submission, scrum_masters)

            if support_mail_error == 'error' or offer_mail_error == "error":
                return Response({
                    "offer": str(offer_mail_res),
                    "support": str(support_mail_res),
                    "message": "Unable to send Support/Offer mail"
                }, status=400)

            return Response({"data": str(support_mail_res), "message": "Support/Offer mail sent"}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=["get"], detail=True, url_name="from_notification")
    def from_notification(self, request, *args, **kwargs):
        try:
            queryset = TimeSheet.objects.filter(id=kwargs.get('pk'))
            serializer = self.serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
