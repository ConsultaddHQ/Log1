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
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from constance import config

from project.swagger import *
from utils_app.mailing import send_email
from api_key.permissions import HasAPIKey
from activity.views import create_activity
from marketing.models import Submission, User
from attachment.models import create_attachment
from utils_app.models import MapMail, ObjectGroup
from utils_app.aws_utils import download_s3_object
from notification.models import Notification, FCMDevice
from utils_app.utils import delete_temp_file, export_to_csv
from marketing.utils import date_filter, get_authenticated_users
from consultant.models import ConsultantPOC, Consultant, ConsultantRateRevision
from utils_app.thred_mail import send_email as send_email_, send_email_attachment_multiple, send_mail_in_thread

from notification.utils import push_notification_consultant
from utils_app.slack_notification import MessageCard as slack
from log1.utils import DONT_HAVE_ACCESS, ERROR_MSG, get_time_filter, get_page_limits, write_exception
from project.models import ConsultantFeedback, Project, ProjectStatus, ProjectOrder, TimeSheet, ProjectSupport, \
    SupportStatus, ConsultantLeave, Leave, TimesheetRequest, TimetrackEvent, ProjectPaymentTerm
from project.utils import ProjectUtil, create_remote_consultant, set_consultant_password, get_attachment_status, \
    fetch_project_status, create_checklist, diff_month_days, support_assignment_mail, send_employer_change_notification, \
    mark_in_active, create_notification_and_send_push, get_country
from project.serializers import ProjectSerializer, ProjectGetSerializer, ProjectOrderSerializer, FinanceSerializer, \
    ProjectSupportSerializer, ConsultantTimeSheetSerializer, LeaveSerializer, ConsultantLeaveSerializer, \
    TimesheetRequestSerializer, TimetrackEventSerializer, ProjectPaymentTermSerializer, \
    ConsultantRevisionViewSetSerializer


# Route - /project/
class ProjectViewSets(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def fetch_scrum_masters(request):
        scrum_masters = list(User.objects.filter(
            team=request.user.team, role__name__in=['admin', 'proxy'], account_login=True
        ).values_list('email', flat=True))
        return scrum_masters

    @staticmethod
    def consultant_mail_on_joining(project, password, new_user, request):
        try:
            mail_data = {
                'template': '../templates/consultant_account_creation.html',
                'subject': f'Your account created on Consultadd Time Track App',
                'to': [project.consultant.email], 'cc': [config.FINANCE, 'yash.j@consultadd.com'],
                'bcc': ['shreyas.k@consultadd.com'],
                'context': {
                    'iphone_link': config.IPHONE_APP_LINK, 'android_link': config.ANDROID_APP_LINK,
                    'password': password, 'new_user': new_user, 'consultant_name': project.consultant.name,
                    'client': project.submission.client.title(), 'consultant_email': project.consultant.email,
                },
            }
            res, msg = send_email(mail_data, config.RELATIONS, request=request)
            if not msg:
                return res, "error"
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    @staticmethod
    def send_offer_received_mail(project, scrum_masters, request):
        try:
            submission = project.submission
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, submission.marketing_team.email]

            cc = [config.SUPERADMIN, submission.created_by.email] + scrum_masters

            consultant = project.submission.consultant
            recruiter = consultant.recruiter
            retention = consultant.relation
            if recruiter:
                cc.append(recruiter.email)

            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            if project.employer:
                employer = project.employer
            else:
                employer = project.submission.employer
            mail_data = {
                'to': to, 'cc': cc, 'bcc': [],
                'template': '../templates/offer.html',
                'subject': f'Offer Received for {consultant.name} :: {submission.client} :: {project_start_date} :: '
                           f'{submission.client} :: {submission.vendor.name}',
                'context': {
                    'consultant_email': consultant.email, 'job_title': submission.lead.job_title,
                    'rate': project.rate, 'con_rate': consultant.rate, 'start': project_start_date,
                    'employer': employer, 'client_name': submission.client, 'consultant_name': consultant.name,
                    'vendor_company': submission.vendor.name, 'marketer_name': submission.created_by.employee_name,
                },
            }
            res, msg, mail_id = send_email_(mail_data, submission.created_by.email, request=request)

            if not msg:
                return res, "error"
            content_type = ContentType.objects.get(model="project")
            mail_object = MapMail(mail_id=res, object_id=project.id, content_type=content_type, from_mail_id=mail_id)
            mail_object.save()
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    @staticmethod
    def send_support_mail(project, scrum_masters, request):
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
                response, error = download_s3_object(resume.first().attachment_file.name)
                if not error:
                    path.append(response)

            consultant = project.submission.consultant
            recruiter = consultant.recruiter
            retention = consultant.relation
            cc = [config.RECRUITMENT, config.RELATIONS, submission.marketing_team.email, submission.created_by.email]
            cc = cc + scrum_masters

            recruiter_name = "NA"
            if recruiter:
                recruiter_name = recruiter.employee_name
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            if project.employer:
                employer = project.employer
            else:
                employer = project.submission.employer
            mail_data = {
                'template': '../templates/support.html',
                'to': [config.ENGINEERING], 'cc': cc, 'bcc': [], 'attachments': path,
                'subject': f'Support Initiation for {consultant.name} {submission.client} {submission.lead.city}',
                'context': {
                    'employer': employer, 'marketer_name': submission.created_by.employee_name,
                    'location': submission.lead.city, 'consultant_location': consultant.current_city,
                    'job_title': submission.lead.job_title, 'consultant_phone_no': consultant.phone_no,
                    'recruiter_name': recruiter_name, 'start': project_start_date, 'recordings': recordings,
                    'consultant_name': consultant.name, 'consultant_email': consultant.email, 'notes': notes,
                    'client_name': submission.client, 'jd': submission.lead.job_desc.replace("\n", " ;newline; "),
                },
            }
            # need to change here
            mail_id = None
            from_mail = submission.created_by.email
            email_object = MapMail.objects.filter(content_type__model="project", object_id=project.id).first()
            if email_object:
                mail_id = email_object.mail_id
                from_mail = email_object.from_mail_id

            res, msg, mail_id = send_email_attachment_multiple(mail_data, from_mail, request, mail_id)
            delete_temp_file(path)
            if not msg:
                return res, "error"
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    def send_support_offer_mail(self, project, scrum_masters, request):
        offer_res, offer_msg = self.send_offer_received_mail(project, scrum_masters, request)
        support_res, support_msg = self.send_support_mail(project, scrum_masters, request)
        engineer = get_object_or_404(User, employee_id=request.data['engineer']) \
            if request.data.get('engineer', None) else None
        # if engineer:
        #     support = get_object_or_404(ProjectSupport, project=project, support=engineer)
        #     support_assignment_mail(support, request)
        message = "Project created"
        exception_msg = "Mail sent"
        if support_msg == 'error' and offer_msg == 'error':
            message = "Project created, but unable to send Support and Offer mail"
            exception_msg = f"Support: {support_res}, Offer: {offer_res}"

        elif support_msg == 'error':
            message = "Project created, but unable to send Support mail"
            exception_msg = f"Support: {support_res}"

        elif offer_msg == 'error':
            message = "Project created, but unable to send Offer mail"
            exception_msg = f"Offer: {offer_res}"

        return message, exception_msg

    @staticmethod
    def po_mail(project, path, scrum_master_email, po_type, request):
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

            if project.employer:
                employer = project.employer
            else:
                employer = project.submission.employer
            mail_data = {
                'template': '../templates/po.html',
                'to': to, 'cc': cc, 'bcc': [], 'attachments': path,
                'subject': f'On Boarding of {consultant.name} :: {project.employer} :: {project_start_date} :: '
                           f'{submission.client} :: {submission.vendor.name}',
                'context': {
                    'marketer_name': submission.created_by.employee_name, 'employer': employer,
                    'job_title': submission.lead.job_title, 'vendor_number': vendor_contact.number,
                    'client_address': project.client_address, 'vendor_address': project.vendor_address,
                    'vendor_company': submission.lead.vendor_company.name, 'client_name': submission.client,
                    'type': po_type, 'consultant_name': consultant.name, 'vendor_email': vendor_contact.email,
                    'invoicing_period': project.invoicing_period, 'reporting_details': project.reporting_details,
                    'payment_term': project.payment_term, 'consultant_email': consultant.email, 'rate': project.rate,
                    'con_rate': int(consultant.rate), 'vendor_name': vendor_contact.name, 'start': project_start_date,
                },
            }

            mail_id = None
            from_mail = marketer.email
            email_object = MapMail.objects.filter(content_type__model="project", object_id=project.id).first()
            if email_object:
                mail_id = email_object.mail_id
                from_mail = email_object.from_mail_id

            res, msg, email_id = send_email_attachment_multiple(mail_data, from_mail, request, mail_id)
            if not msg:
                return res, "error"
            return res, "ok"
        except Exception as error:
            write_exception(message=f"Offer mail error for {marketer.email}: {error}", request=request)
            return error, "error"

    @staticmethod
    def po_end_mail(project, scrum_master_email, po_type, request):
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
            if marketer.account_login:
                cc = [marketer.email, config.SUPERADMIN] + scrum_master_email
            else:
                cc = [config.SUPERADMIN] + scrum_master_email
            if recruiter and recruiter.account_login:
                cc.append(recruiter.email)
            if retention and retention.account_login:
                cc.append(retention.email)

            project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            project_end_date = None
            if project.end_date:
                project_end_date = datetime.strptime(str(project.end_date), '%Y-%m-%d').strftime('%m/%d/%Y')
            if project.employer:
                employer = project.employer
            else:
                employer = project.submission.employer
            mail_data = {
                'to': to, 'cc': cc, 'bcc': [],
                'template': '../templates/po_termination.html',
                'subject': f"{consultant.name}'s {po_type} :: {employer} :: "
                           f'{project_start_date} :: {submission.client} :: {submission.vendor.name}',
                'context': {
                    'vendor_number': vendor_number, 'client_name': submission.client,
                    'reason': project.statuses.get(is_current=True).get_status_display(),
                    'reporting_details': project.reporting_details, 'end': project_end_date,
                    'consultant_name': consultant.name, 'consultant_email': consultant.email,
                    'vendor_email': vendor_email, 'employer': employer, 'rate': project.rate,
                    'vendor_company': submission.lead.vendor_company.name, 'po_type': po_type,
                    'job_title': submission.lead.job_title, 'marketer_name': marketer.employee_name,
                    'vendor_address': project.vendor_address, 'client_address': project.client_address,
                    'vendor_name': vendor_name, 'start': project_start_date, 'remark': project.feedback,
                }
            }

            # mail_id = None
            # from_mail = marketer.email
            # email_object = MapMail.objects.filter(content_type__model="project",object_id=project.id).first()
            # if email_object:
            #     mail_id = email_object.mail_id
            #     from_mail = email_object.from_mail_id   

            # if mail_id:                     
            #     res1, msg1, mail_id = send_mail_in_thread(mail_data, from_mail, request, mail_id)
            # else:
            res1, msg1, mail_id = send_email_(mail_data, marketer.email, request=request)

            if msg1:
                res1 = "mail send"

            mail_data_eng = {
                'to': [config.ENGINEERING], 'cc': [], 'bcc': [],
                'template': '../templates/po_termination_engineering.html',
                'subject': f"{consultant.name}'s {po_type} :: {project_start_date} :: {submission.client} ::"
                           f" {submission.vendor.name}",
                'context': {
                    'consultant_name': consultant.name, 'end': project_end_date,
                    'employer': project.submission.employer, 'location': project.city,
                    'reason': project.statuses.get(is_current=True).get_status_display(),
                    'consultant_email': consultant.email, 'client_name': submission.client,
                    'vendor_company': submission.lead.vendor_company.name, 'po_type': po_type,
                    'feedback': project.feedback if project.feedback else "Not updated on Log1",
                    'project_duration': f"{diff_month_days(project.start_date, project.end_date)} months",
                }
            }
            mail_id = None
            from_mail = marketer.email
            email_object = MapMail.objects.filter(content_type__model="project", object_id=project.id).first()
            if email_object:
                mail_id = email_object.mail_id
                from_mail = email_object.from_mail_id

            if mail_id:
                res2, msg2, mail_id = send_mail_in_thread(mail_data, from_mail, request, mail_id)
            else:
                res2, msg2, mail_id = send_email_(mail_data, from_mail, request=request)

            if msg2:
                res2 = "mail send"

            return f"Res1: {res1} and res2: {res2}", "ok"
        except Exception as error:
            write_exception(message="Offer mail error for {}".format(marketer.email) + str(error))
            return error, "error"

    @retrieve_project
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

    @list_project
    def list(self, request, *args, **kwargs):
        url = ""
        status_count = {}
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_for = request.GET.get('filter_for', None)
        filter_json = request.GET.get('filter_json', None)
        export = json.loads(request.GET.get('export', 'false'))
        filter_by_time = request.GET.get('filter_by_time', None)
        filter_by_lead = request.GET.get('filter_by_lead', None)

        try:
            # search project by client and consultant
            if filter_for == 'my':
                projects = Project.objects.filter(submission__created_by=request.user).exclude(
                    submission__status='archive'
                )
            elif filter_for == 'handover':
                users = get_authenticated_users(request)
                users.remove(request.user)
                projects = Project.objects.filter(submission__created_by__in=users)
            elif filter_for == 'team':
                projects = Project.objects.filter(Q(submission__marketing_team=request.user.team) |
                                                  Q(submission__marketing_team__in=request.user.associated_to.all()))
            else:
                projects = Project.objects.exclude(submission__status='archive')

            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(city__istartswith=query) |
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if filter_json and json.loads(filter_json):
                filters = json.loads(filter_json)

                created = filters.get('created', None)
                if created:
                    projects = date_filter(projects, created, 'created')

                if 'client' in filters and len(filters["client"]) > 0:
                    projects = projects.filter(submission__client__in=filters['client'])

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    projects = projects.filter(submission__created_by_id__in=filters['marketer'])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    projects = projects.filter(submission__lead__vendor_company__name__in=filters['vendor'])

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    projects = projects.filter(
                        Q(consultant__name__in=filters['consultant']) |
                        Q(submission__consultant_marketing__consultant__name__in=filters['consultant'])
                    )

                if 'remote' in filters:
                    projects = projects.filter(is_remote=filters['remote'])

                if 'work_type' in filters:
                    projects = projects.filter(submission__work_type__in=filters['work_type'])

                if 'status' in filters and len(filters["status"]) > 0:
                    status_count = {
                        "total": projects.count(),
                        "new": projects.filter(statuses__status='new', statuses__is_current=True).count(),
                        "joined": projects.filter(statuses__status='joined', statuses__is_current=True).count(),
                        "received": projects.filter(statuses__status='received', statuses__is_current=True).count(),
                        "complete": projects.filter(statuses__status='complete', statuses__is_current=True).count(),
                        "on_boarded": projects.filter(statuses__status='on_boarded', statuses__is_current=True).count(),
                        "cancelled": projects.filter(statuses__status__istartswith='cancelled',
                                                     statuses__is_current=True).count(),
                        "terminated": projects.filter(statuses__status__istartswith='terminated',
                                                      statuses__is_current=True).count(),
                        "not_joined": projects.filter(statuses__status='on_boarded', statuses__is_current=True,
                                                      start_date__lt=date.today()).count()
                    }

                    not_joined = Project.objects.none()
                    if 'not_joined' in filters["status"]:
                        not_joined = projects.filter(
                            statuses__status='on_boarded', statuses__is_current=True, start_date__lt=date.today()
                        )
                    projects = projects.filter(statuses__status__in=filters['status'], statuses__is_current=True)
                    projects = (projects | not_joined).distinct('id')

            if filter_by_lead:
                projects = projects.filter(submission__work_type=filter_by_lead)

            if filter_by_time:
                projects = get_time_filter(projects, filter_by_time)

            if not status_count:
                status_count = {
                    "total": projects.count(),
                    "new": projects.filter(statuses__status='new', statuses__is_current=True).count(),
                    "joined": projects.filter(statuses__status='joined', statuses__is_current=True).count(),
                    "received": projects.filter(statuses__status='received', statuses__is_current=True).count(),
                    "complete": projects.filter(statuses__status='complete', statuses__is_current=True).count(),
                    "on_boarded": projects.filter(statuses__status='on_boarded', statuses__is_current=True).count(),
                    "cancelled": projects.filter(
                        statuses__status__istartswith='cancelled', statuses__is_current=True
                    ).count(),
                    "terminated": projects.filter(
                        statuses__status__istartswith='terminated', statuses__is_current=True
                    ).count(),
                    "not_joined": projects.filter(
                        statuses__status='on_boarded', statuses__is_current=True, start_date__lt=date.today()
                    ).count()
                }

            projects = projects.order_by('id').distinct('id')

            data_count = {
                "status": {
                    "new": status_count["new"],
                    "total": status_count["total"],
                    "joined": status_count["joined"],
                    "received": status_count["received"],
                    "complete": status_count["complete"],
                    "cancelled": status_count["cancelled"],
                    "terminated": status_count["terminated"],
                    "not_joined": status_count["not_joined"],
                    "on_boarded": status_count["on_boarded"]
                },
                "job_type": {
                    "w2": projects.filter(submission__work_type='w2').count(),
                    "c2c": projects.filter(submission__work_type='c2c').count(),
                    "full_time": projects.filter(submission__work_type='full_time').count()
                },
                "project_type": {
                    "in_house": projects.filter(is_remote=True).count(),
                    "consultant": projects.filter(is_remote=False).count()
                },
            }

            if sort_by in ['created', 'modified']:
                order_by = f"-{sort_by}"
            elif sort_by == 'consultant':
                order_by = '-submission__consultant_marketing__consultant__name'
            else:
                order_by = '-modified'

            projects = Project.objects.filter(id__in=projects.values('id')).order_by(order_by)

            if export:
                col_name = [
                    {"name": "consultant_name", "display_name": "Consultant Name"},
                    {"name": "marketer_name", "display_name": "Marketer Name"},
                    {"name": "client", "display_name": "Client Name"},
                    {"name": "employer", "display_name": "Employer Name"},
                    {"name": "company_name", "display_name": "Company Name"},
                    {"name": "start_date", "display_name": "Start Date"},
                    {"name": "end_date", "display_name": "End Date"},
                    {"name": "duration", "display_name": "Duration"},
                    {"name": "city", "display_name": "City"},
                    {"name": "is_remote", "display_name": "Remote"},
                    {"name": "status", "display_name": "Status"},
                    {"name": "rate", "display_name": "Rate"}
                ]
                serializer = self.serializer_class(projects, many=True)
                url = export_to_csv(
                    serializer.data, col_name, f"po_{datetime.now().strftime('%d-%B-%Y')}.csv", request, "Project List"
                )

            serializer = self.serializer_class(projects[first: last], many=True)
            return Response({
                "counts": data_count, "data": serializer.data, "total": projects.count(), "file_url": url
            }, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        sub_id = request.data.get('submission')
        try:
            users = get_authenticated_users(request)
            sub = get_object_or_404(Submission, id=sub_id, created_by__in=users)
            if hasattr(sub, 'project'):
                return Response({"message": "Project already exist"}, status=406)

            # Adding Remote consultant
            remote_consultant = create_remote_consultant(request)
            if remote_consultant:
                consultant = remote_consultant
            else:
                consultant = sub.consultant

            if request.data.get('work_type') and request.data.get('work_type', sub.work_type) != sub.work_type:
                sub.work_type = request.data.get('work_type')
                sub.save()
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

                # Creating Project training Checklist
                create_checklist(project.id, request)

                # Activity
                desc = f"Purchase order created with start date of {project.start_date} and support mail is sent"
                create_activity(sub.id, 'submission', request.user, desc, 'created')

                # support_assignment_mail(support, request)
                message, error_msg = self.send_support_offer_mail(project, self.fetch_scrum_masters(request), request)
                serializer = self.serializer_class(project)
                return Response({"message": message, "data": serializer.data, "exception": error_msg}, status=201)
            return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @update_project
    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            err = None
            new_status = request.data.get('status', None)
            project = get_object_or_404(Project, id=project_id)
            prev_employer = project.employer
            prev_status_obj = project.statuses.get(is_current=True)
            prev_rate, prev_start_date = project.rate, project.start_date
            all_status, cancellation_status, termination_status = fetch_project_status()

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

            activity_created = False

            if prev_employer != project.employer and request.data['status'] not in ['new', 'received', 'on_boarded']:
                data = {"prev_employer": prev_employer, "new_employer": project.employer}
                activity_created = True
                send_employer_change_notification(project, data, request)

            util = ProjectUtil(project, request)
            desc = f"Purchase order is updated"
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
                    desc = f"Purchase order status changed to Received"
                    util.send_receive_notification()
                    project.is_msg_sent = True
                    project.save()

                # Project Joined
                elif new_status == 'joined':
                    project.consultant.status = 'on_project'
                    project.consultant.save()
                    desc = f"PO status changed to Joined and Timesheet APP access mail is sent to consultant"
                    if marketing.status == 'open':
                        marketing.end = date.today()
                        marketing.status = 'close'
                        marketing.save()

                    # Creating first week Timesheet on project status change to joined
                    if project.submission.work_type == 'c2c':
                        util.create_timesheet()

                    # Creating first week Timesheet on project status change to joined
                    util.assign_leave()

                    # Setting password for User (consultant)
                    password, new_user = set_consultant_password(project.consultant)
                    resp, err = self.consultant_mail_on_joining(project, password, new_user, request)
                    util.send_join_notification()

                # Project Cancelled
                elif prev_status_obj.status not in cancellation_status and new_status in cancellation_status:
                    marketing.status = 'open'
                    marketing.save()
                    project.support.update(end=datetime.now())
                    desc = f"Purchase order status changed to Cancelled and cancellation mail is sent"
                    resp, err = self.po_end_mail(project, scrum_masters, 'PO Cancelled', request)
                    po_status = project_status_obj.get_status_display()
                    util.send_cancellation_notification(po_status)

                # Project Terminated
                elif prev_status_obj.status not in termination_status and new_status in termination_status:
                    project.consultant.status = 'on_bench'
                    project.consultant.save()
                    project.support.update(end=datetime.now())
                    desc = f"Purchase order status changed to Terminated and termination mail is sent"
                    po_status = project_status_obj.get_status_display()
                    resp, err = self.po_end_mail(project, scrum_masters, 'PO Terminated', request)
                    util.send_termination_notification(po_status)

                # Project Completed
                elif prev_status_obj.status != 'complete' and new_status == "complete":
                    project.consultant.status = 'on_bench'
                    project.consultant.save()
                    project.support.update(end=datetime.now())
                    desc = f"Purchase order status changed to Complete"
                    resp, err = self.po_end_mail(project, scrum_masters, 'project completed', request)
                    util.send_completion_notification()

                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')

            # Activity
            if prev_rate != project.rate:
                desc = f"Purchase order rate is updated"
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
                activity_created = True

            if str(prev_start_date) != str(project.start_date):
                desc = f"Purchase order start_date is updated"
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
                activity_created = True

            if not activity_created:
                desc = f"Purchase order is updated"
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
            serializer = self.serializer_class(project)

            return Response({"data": serializer.data, "error": err, "message": "Project updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @project_mail_to_onboard
    @action(methods=['get'], detail=False, url_path="mail_to_onboard")
    def mail_to_onboard(self, request):
        try:
            path = []
            project_id = request.GET.get('project_id', None)
            if project_id:

                project = get_object_or_404(Project, id=project_id)
                result = get_attachment_status(project)
                if not result["status"]:
                    return Response({"message": "Complete all details"}, status=400)

                prev_status = project.statuses.filter(is_current=True).first()
                po_type = 'created'
                if prev_status.status == 'on_boarded':
                    po_type = 'updated'

                for i in project.attachments.filter(
                        attachment_type__in=['work_order_signed', 'work_order_msa_signed', 'msa_signed']):
                    try:
                        response, error = download_s3_object(i.attachment_file.name)
                        path.append(response)
                    except Exception as error:
                        write_exception(error, request)

                res, error = self.po_mail(project, path, self.fetch_scrum_masters(request), po_type, request)

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

                        # Activity
                        desc = "Purchase order status is updated to Onboarded and Onboarding mail is sent"
                        create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
                    return Response({"message": "On-boarding mail sent", "error": res}, status=200)
                return Response({"data": str(res)}, status=400)
            else:
                return Response({"message": "Invalid Id"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @project_send_support_mail
    @action(methods=['get'], detail=True, url_path="send_support_mail")
    def send_support_and_offer_mail(self, request, pk):
        try:
            project = get_object_or_404(Project, id=pk)
            message, exception_msg = self.send_support_offer_mail(project, self.fetch_scrum_masters(request), request)
            if exception_msg != 'Mail sent':
                return Response(
                    {"exception": exception_msg, "message": "Unable to send Support or Offer mail"}, status=400
                )
            return Response({"data": exception_msg, "message": "Support and Offer mail sent"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @project_fields
    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, pk):
        try:
            project = get_object_or_404(Project, id=pk)
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

    @project_remove_remote
    @action(methods=['get'], detail=True, url_path='remove_remote')
    def remove_remote(self, request, pk):
        try:
            project = get_object_or_404(Project, id=pk)
            if project.is_remote:
                project.is_remote = False
                project.consultant = project.submission.consultant
                project.save()
                return Response({"message": "Remote consultant is removed"}, status=200)
            else:
                return Response({"message": "Project is not remote"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


class ProjectPaymentTermViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin, RetrieveModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = ProjectPaymentTerm.objects.all()
    serializer_class = ProjectPaymentTermSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            query = request.GET.get('query')
            queryset = ProjectPaymentTerm.objects.all()
            project_type = request.GET.get('project_type')

            if project_type:
                queryset = queryset.filter(project__submission__work_type=project_type)
            if query:
                query = query.lstrip().replace(':amp:', '&')
                queryset = queryset.filter(
                    project__submission__consultant_marketing__consultant__name__istartswith=query)

            serializer = ProjectPaymentTermSerializer(queryset[first:last], many=True)
            return Response({"data": serializer.data, "count": len(serializer.data)}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            data = {
                'id': project.id,
                'rate': project.rate,
                'client_name': project.submission.client,
                'remote_engineer': project.consultant.name,
                'project_type': project.submission.work_type,
                'country': get_country(project.submission.lead.city),
                'consultant_name': project.submission.consultant.name,
                'marketer_name': project.submission.created_by.employee_name,
                'vendor_company': project.submission.lead.vendor_company.name,
            }
            return Response({"project_info": data}, status=status.HTTP_200_OK)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not 'superadmin' in roles and not 'admin' in roles and not 'scrum master' in roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=status.HTTP_403_FORBIDDEN)

            project = get_object_or_404(Project, id=request.data.get("project_id"))

            ProjectPaymentTerm.objects.create(
                payment_term=request.data.get("payment_term", None),
                payment_term_type=request.data.get("payment_term_type", None),
                comment=request.data.get("comment", None),
                created_by=request.user,
                project=project
            )
            return Response({"message": "Payment Term Created Successfully"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not 'superadmin' in roles and not 'admin' in roles and not 'scrum master' in roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=status.HTTP_403_FORBIDDEN)

            payment_term = get_object_or_404(ProjectPaymentTerm, id=kwargs.get('pk'))
            payment_term.payment_term = request.data.get("payment_term")
            payment_term.payment_term_type = request.data.get("payment_term_type")
            payment_term.comment = request.data.get("comment")
            payment_term.save()

            des = f"{request.user} has changed the project payment term details"
            create_activity(payment_term.id, 'projectpaymentterm', request.user, des, 'updated')
            return Response({"message": "Payment Term Updated Successfully"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='payment_term_types')
    def payment_term_types(self, request):
        try:
            return Response(ProjectPaymentTerm.PAYMENT_TERM_TYPE, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='project_list')
    def project_list(self, request, ):
        try:
            ID_MAX_LENGTH = 4
            project_list = []
            query = request.GET.get('query', '').lower().replace("po-", "")
            project_ids_with_payment_terms = ProjectPaymentTerm.objects.values_list('project_id', flat=True)

            if len(query) == ID_MAX_LENGTH:
                queryset = Project.objects.exclude(id__in=project_ids_with_payment_terms).filter(id=query)
            else:
                queryset = Project.objects.exclude(id__in=project_ids_with_payment_terms).exclude(
                    submission__status='archive').filter(
                    id__istartswith=query, statuses__status='joined', statuses__is_current=True
                )
            for project in queryset:
                data = {
                    "id": project.id,
                    'rate': project.rate,
                    'submission_id': project.submission.id,
                    'client_name': project.submission.client,
                    'remote_engineer': project.consultant.name,
                    'project_type': project.submission.work_type,
                    'country': get_country(project.submission.lead.city),
                    'consultant_name': project.submission.consultant.name,
                    'marketer_name': project.submission.created_by.employee_name,
                    'vendor_company': project.submission.lead.vendor_company.name,
                }
                project_list.append(data)
            return Response({"project_list": project_list}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Route - /project/<project_id>/support/
class ProjectSupportViewSet(GenericViewSet, RetrieveModelMixin, ListModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = ProjectSupport.objects.all()
    serializer_class = ProjectSupportSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def fetch_scrum_masters(request):
        scrum_masters = list(User.objects.filter(
            team=request.user.team, role__name__in=['admin', 'proxy'], account_login=True
        ).values_list('email', flat=True))
        return scrum_masters

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
            serializer = ProjectSupportSerializer(project.support.all().order_by('-created'), many=True)
            if hasattr(project, 'description'):
                description = project.description
                is_description = False if not description.timezone or not description.technology else True
            else:
                is_description = False
            return Response({"data": serializer.data, "is_project_description": is_description}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @create_project_support
    def create(self, request, *args, **kwargs):
        try:
            is_proxy_support = request.data.get('is_proxy_support', False)
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
            support_person = get_object_or_404(User, id=request.data.get('support', None))
            supports = project.support.filter(end=None, is_proxy_support=False)
            proxy_start_date = request.data.get('proxy_start_date', None)
            proxy_support_person = request.data.get('proxy_support_person', None)
            if proxy_support_person and proxy_start_date:
                proxy_support_person = get_object_or_404(User, id=proxy_support_person)
                if supports.filter(support=proxy_support_person, statuses__frequency="active",
                                   statuses__is_current=True, project=project):
                    return Response(
                        {"message": "Proxy support person should be different than active support person"}, status=400
                    )
                if {'support_id': proxy_support_person.id} in supports.values('support_id'):
                    return Response({"message": "Support person is already active for this support"}, status=400)
                ProjectSupport.objects.create(
                    project=project, is_proxy_support=True, start=proxy_start_date, support=proxy_support_person
                )

            if is_proxy_support and supports.filter(support=support_person, statuses__frequency="active",
                                                    statuses__is_current=True, project=project):
                return Response(
                    {"message": "Proxy support person should be different than active support person"}, status=400
                )

            if {'support_id': support_person.id} in supports.values('support_id'):
                return Response({"message": "Support person is already active for this support"}, status=400)

            end = request.data.get('end', None)
            start = request.data.get('start', None)
            if not start:
                return Response({"message": "Start date can not be empty"}, status=400)

            support_qs = True if len(project.support.all()) > 1 else False
            project_support = ProjectSupport.objects.create(
                project=project, is_proxy_support=request.data.get('is_proxy_support', False),
                support=support_person, start=start, end=end, feedback=request.data.get('description', None),
            )
            if not project_support.is_proxy_support:
                SupportStatus.objects.create(
                    is_current=True, support=project_support, change_date=start, frequency=request.data.get('status'),
                )

            if request.user.id == support_person.id:
                if project_support.is_proxy_support:
                    desc = f"{request.user.employee_name} added himself as proxy person"
                else:
                    desc = f"{request.user.employee_name} added himself as support person"
            else:
                if project_support.is_proxy_support:
                    desc = f"{request.user.employee_name} added {support_person.employee_name} as proxy person"
                else:
                    desc = f"{request.user.employee_name} added {support_person.employee_name} as support person"
            create_activity(project.id, 'projectsupport', request.user, desc, 'created')

            message = ""
            if not support_qs:
                message, exception_msg = support_assignment_mail(project_support, request)
                if exception_msg != 'Mail sent':
                    message = "Unable to send support assignment mail &"
                    # return Response(
                    #     {"exception": exception_msg, "message": "Unable to send support assignment mail"}, status=400
                    # )
                else:
                    message = "Support assignment mail send &"

            return Response({"message": message + "Support is added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @update_project_support
    def update(self, request, *args, **kwargs):
        try:
            support = get_object_or_404(ProjectSupport, id=kwargs.get('pk'))
            serializer = ProjectSupportSerializer(support, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            desc = f"{request.user.employee_name} updated support details"
            create_activity(support.project.id, 'projectsupport', request.user, desc, 'updated')
            return Response({"message": "Support is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @project_support_status
    @action(methods=['put'], detail=True, url_path="status")
    def status(self, request, project_id, pk):
        try:
            support = get_object_or_404(ProjectSupport, id=pk, project_id=project_id)
            status = request.data.get('status')
            start = request.data.get('change_date')
            prev_support = support.statuses.filter(is_current=True)
            if prev_support:
                prev_support = prev_support.first()
                if prev_support.frequency != status:
                    prev_support.is_current = False
                    prev_support.save()
                    SupportStatus.objects.create(is_current=True, support=support, change_date=start, frequency=status)
            else:
                SupportStatus.objects.create(is_current=True, support=support, change_date=start, frequency=status)
            desc = f"{request.user.employee_name} updated support status"
            create_activity(support.project.id, 'projectsupport', request.user, desc, 'updated')
            return Response({"message": "Support status is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @project_support_initiate
    @action(methods=['put'], detail=False, url_path="initiate")
    def initiate(self, request, project_id):
        try:
            start = request.data.get('start')
            project = get_object_or_404(Project, id=project_id)
            support_id = request.data.get('support', None)
            support = get_object_or_404(User, id=support_id)

            project_support = ProjectSupport.objects.create(project=project, support=support, start=start)
            SupportStatus.objects.create(
                is_current=True, support=project_support, change_date=start, frequency='active',
            )
            submission = project.submission
            consultant = project.submission.consultant
            to = [project.created_by.email, support.email]
            cc = ['engineering@consultadd.com']

            mail_data = {
                'template': '../templates/support_initiate.html',
                'to': to, 'cc': cc, 'bcc': [],
                'subject': f"{consultant.name}'s support initiated for  {project.submission.client} by"
                           f" {support.employee_name}",
                'context': {
                    'start': project.start_date, 'support_name': support.employee_name, 'client': submission.client,
                    'marketer_name': submission.created_by.employee_name, 'support_email': support.email,
                    'location': submission.lead.city, 'job_title': submission.lead.job_title,
                    'consultant_name': consultant.name, 'consultant_email': consultant.email,
                },
            }

            mail_id = None
            from_mail = support.email
            email_object = MapMail.objects.filter(content_type__model="project", object_id=project.id).first()
            if email_object:
                mail_id = email_object.mail_id
                from_mail = email_object.from_mail_id
                # need to work here
            if mail_id:
                res, msg, mail_id = send_mail_in_thread(mail_data, from_mail, request, mail_id)
            else:
                res, msg, mail_id = send_email_(mail_data, support.email, request=request)
            if not msg:
                return Response({"message": "Unable to send mail"}, status=400)
            return Response({"message": "Support is initiated", "result": res}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @project_support_remove
    @action(methods=['delete'], detail=True, url_path="remove")
    def remove_support(self, request, project_id, pk):
        try:
            if 'admin' in request.user.roles and 'engineer' in request.user.roles:
                support = get_object_or_404(ProjectSupport, id=pk, project_id=project_id)
                desc = f"{request.user.employee_name} removed {support.support.employee_name} as support person"
                create_activity(support.project.id, 'projectsupport', request.user, desc, 'deleted')
                support.delete()
                return Response({"message": "Support is removed"}, status=202)
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @project_support_update_details
    @action(methods=['put'], detail=True, url_path="update_details")
    def details(self, request, project_id, pk):
        try:
            msg = {}
            data = request.data
            support = get_object_or_404(ProjectSupport, id=pk, project_id=project_id)
            prev_support = support.statuses.filter(is_current=True).first()

            project = support.project
            proxy_start_date = request.data.get('proxy_start_date', None)
            proxy_support_person = request.data.get('proxy_support_person', None)
            supports = project.support.filter(end=None, is_proxy_support=False)
            if proxy_support_person and proxy_start_date:
                proxy_support_person = get_object_or_404(User, id=proxy_support_person)
                if supports.filter(support=proxy_support_person, statuses__frequency="active",
                                   statuses__is_current=True, project=project):
                    return Response(
                        {"message": "Proxy support person should be different than active support person"}, status=400
                    )
                if {'support_id': proxy_support_person.id} in supports.values('support_id'):
                    return Response({"message": "Support person is already active for this support"}, status=400)
                ProjectSupport.objects.create(
                    project=project, is_proxy_support=True, start=proxy_start_date, support=proxy_support_person
                )
                desc = f"{request.user.employee_name} added proxy support details"
                create_activity(support.project.id, 'projectsupport', request.user, desc, 'updated')

            if support.is_proxy_support is True and support.support.id != data.get('support'):
                supports = ProjectSupport.objects.filter(
                    statuses__is_current=True, is_proxy_support=False,
                    support_id=data.get('support'), statuses__frequency="active", project_id=project_id
                )
                if supports:
                    return Response(
                        {"message": "Proxy support person should be different than active support person"}, status=400
                    )

                support.support_id = data.get('support')
                support.save()
                msg = {'var1': 'person', 'var2': 'proxy'}

            if prev_support and prev_support.frequency != data['status']:
                prev_support.is_current = False
                prev_support.save()
                SupportStatus.objects.create(
                    is_current=True, support=support, frequency=data['status'], change_date=data['change_date']
                )
                msg = {"var1": "status"}

            serializer = ProjectSupportSerializer(support, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            desc = f"{request.user.employee_name} updated {msg.get('var2', '')} support {msg.get('var1', 'details')} "
            create_activity(support.project.id, 'projectsupport', request.user, desc, 'updated')

            # need to add slack card here
            if data.get('status') == "independent":
                # adding consultant update here
                user_list = []
                feedback = ConsultantFeedback.objects.create(
                    project=project,
                    created_by=request.user,
                    department='engineering',
                    rating=request.data.get('rating', None),
                    verdict=request.data.get('verdict', None),
                    consultant_id=request.data.get('consultant_id'),
                    description=request.data.get('description'),
                    feedback_type=request.data.get('feedback_type'),
                )

                consultant = feedback.consultant
                emp_name = request.user.employee_name
                feedback_type = feedback.get_feedback_type_display()

                tags = request.data.get('tagged_user', [])
                if len(tags) > 0:
                    for tag in tags:
                        user = get_object_or_404(User, id=tag)
                        user_list.append(user)

                title = f"{emp_name} tagged you in a {consultant.name}'s {feedback_type} feedback."
                create_and_send_notification(consultant, feedback, title, user_list, request)

                # POC Notification
                pocs = consultant.pocs.all()
                user_list = [user.poc for user in pocs]
                title = f"{feedback_type} feedback added for {consultant.name} by {emp_name} from {feedback.department}."
                create_and_send_notification(consultant, feedback, title, user_list, request)

                # Activity
                desc = f"{emp_name} added {feedback_type} feedback"
                create_activity(consultant.id, 'consultant', request.user, desc, 'created')

                employee_name = f"<@{request.user.slack_id}>" if request.user.slack_id else request.user.employee_name
                payload = {
                    "activity_title": f"Support marked independent by {employee_name} for below mentioned project",
                    "project_id": project_id,
                    "support_end_date": data.get('end'),
                    "feedback": request.data.get('description'),
                    "client_name": support.project.submission.client,
                    "project_start_date": str(support.project.start_date),
                    "consultant_name": support.project.consultant.name,
                    "support_duration":
                        str(datetime.strptime(data['end'], "%Y-%m-%d") - datetime.strptime(
                            str(support.project.start_date), "%Y-%m-%d")).split(",")[0],

                }
                slack.consultant_independent_message_card(payload, self.request)
            return Response({"message": "Support detail is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project_order/
class ProjectOrderViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = ProjectOrder.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectOrderSerializer
    authentication_classes = (TokenAuthentication,)

    @list_project_order
    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.GET.get('project_id'))
            serializer = ProjectOrderSerializer(project.order.all().order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @create_project_order
    def create(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.data.get('project_id'))
            effective_date = request.data.get('effective_date')
            desc = ""
            if request.data.get('field') == 'rate':
                project.rate = request.data.get('value')
                desc = f"Project {project.submission.consultant.name} :: {project.submission.client} rate changed to " \
                       f"{request.data.get('value')} by {request.user.employee_name}"

                # Activity
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')

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
                field=request.data.get('field'), value=request.data.get('value'),
                project=project, created_by=request.user, effective_date=effective_date,
            )
            project.save()

            if request.FILES.getlist('file'):
                attachments = project.attachments.all()
                for attachment in attachments:
                    attachment.is_active = False
                    attachment.save()

                for file in request.FILES.getlist('file'):
                    file_data = {
                        "file": file, "model": "project", "object_id": project.id,
                        "creator": request.user, "type": request.data.get('file_type'),
                    }
                    create_attachment(file_data)
            create_activity(order.id, 'projectorder', request.user, desc, 'created')
            serializer = self.serializer_class(project.order.all(), many=True)
            return Response({"data": serializer.data, "message": "Project order created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @update_project_order
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

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /eng_project/
class EngineeringProjectsViewSets(GenericViewSet, ListModelMixin):
    authentication_classes = ()
    permission_classes = (HasAPIKey,)
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @list_eng_project
    def list(self, request, *args, **kwargs):
        try:
            end = request.GET.get("end", None)
            start = request.GET.get("start", None)
            if start and end:
                projects = Project.objects.select_related('submission').filter(modified__range=[start, end])
            else:
                projects = Project.objects.select_related('submission').all()

            recruiter = ConsultantPOC.objects.filter(
                consultant=OuterRef("consultant_id"), end=None, poc_type='recruiter')

            relation = ConsultantPOC.objects.filter(
                consultant=OuterRef("consultant_id"), end=None, poc_type='retention')

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

    def retrieve(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        start = request.GET.get('start', None)
        project_id = request.GET.get('project_id', None)
        timesheet_status = request.GET.get('status', None)
        end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))

        try:
            if project_id:
                projects = Project.objects.filter(id=project_id)
            else:
                projects = Project.objects.filter(
                    Q(statuses__is_current=True, consultant_id=kwargs.get('pk', None)) & (
                            Q(statuses__status__istartswith='terminated') |
                            Q(statuses__status__in=['complete', 'joined', 'extended'])
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
                    if not end:
                        end = date.today().strftime('%Y-%m-%d')
                    queryset = TimeSheet.objects.filter(project__in=ids, start__gte=start, end__lte=end)
                else:
                    queryset = TimeSheet.objects.filter(project__in=ids)
                if timesheet_status:
                    if timesheet_status == 'pending_for_approval':
                        queryset = queryset.filter(status__in=['submitted', 'updated'], is_active=True)
                    else:
                        queryset = queryset.filter(status=timesheet_status, is_active=True)
                else:
                    queryset = queryset.exclude(status='draft')
                total = queryset.count()
                serializer = self.serializer_class(queryset[first:last], many=True)
                return Response({"data": serializer.data, 'total': total}, status=200)
            return Response({"data": {}, 'total': 0}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        consultant_id = request.GET.get('consultant', None)
        consultant_name = request.GET.get('consultant_name', None)

        try:
            project_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue', 'complete',
                'joined', 'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            if consultant_id:
                consultants = Consultant.objects.filter(id=consultant_id)
            elif consultant_name:
                consultants = Consultant.objects.filter(name__istartswith=consultant_name)
            else:
                consultant_ids = Project.objects.filter(
                    statuses__status__in=project_status, statuses__is_current=True
                ).values_list('consultant', flat=True)

                consultants = Consultant.objects.filter(
                    id__in=list(consultant_ids),
                    projects__timesheets__is_active=True,
                    projects__timesheets__status__in=['submitted', 'updated'],
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

    @action(methods=["get"], detail=False, url_name="consultant")
    def consultant(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        end_date = request.GET.get('end', None)
        start_date = request.GET.get('start', None)
        leave_status = request.GET.get('leave_status', '')
        consultant_id = request.GET.get('consultant', None)
        project_type = request.GET.get('project_type', None)
        timesheet_status = request.GET.get('timesheet_status', None)

        try:
            result = []
            project_status = [
                'terminated-fired_performance_issue', 'terminated-fired_security_issue',
                'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                'terminated-fired_budget_issue', 'terminated-resigned_location_issue', 'complete',
                'joined', 'terminated', 'terminated-resigned', 'terminated-resigned_location_issue',
            ]

            if consultant_id:
                consultant = Consultant.objects.filter(id=consultant_id).first()
                if not consultant_id:
                    return Response({"message": "Consultant Not Found"}, status=400)
                project_qs = consultant.projects.all()
            else:
                project_qs = Project.objects.filter(
                    statuses__status__in=project_status, statuses__is_current=True
                )

            if project_type:
                project_qs = project_qs.filter(submission__work_type=project_type)

            timesheet_qs = TimeSheet.objects.filter(project__in=project_qs)
            if start_date:
                timesheet_qs = timesheet_qs.filter(start__gte=start_date)
            if end_date:
                timesheet_qs = timesheet_qs.filter(end__lte=end_date)
            if timesheet_status == 'pending_for_approval':
                timesheet_qs = timesheet_qs.filter(status__in=['submitted', 'updated'], is_active=True)
            elif timesheet_status:
                timesheet_qs = timesheet_qs.filter(status=timesheet_status, is_active=True)
            project_ids = timesheet_qs.filter().order_by('-project_id').distinct('project_id').values_list(
                'project_id', flat=True
            )

            consultant_ids = project_qs.filter(id__in=project_ids).order_by('-consultant_id').distinct('consultant_id') \
                .values_list('consultant_id', flat=True)

            consultants = Consultant.objects.filter(id__in=consultant_ids)

            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = consultants.filter(name__istartswith=query)

            if leave_status:
                consultants = consultants.filter(leaves__status=leave_status)

            project_qs = project_qs.filter(id__in=project_ids, consultant__in=consultants).order_by(
                'consultant_id', 'id').distinct('consultant_id')
            for obj in project_qs[first: last]:
                consultant = obj.consultant
                ts_obj = timesheet_qs.filter(project=obj)
                ts_status = None if not ts_obj else ts_obj.first().status
                ts_qs = TimeSheet.objects.filter(project__consultant=consultant)
                data = {
                    "id": consultant.id,
                    "name": consultant.name,
                    "email": consultant.email,
                    "approval_required": consultant.approval_required,
                    "pending_leave": True
                    if consultant.leaves.filter(status__in=['applied', 'pending']).order_by('created') else False,
                    "pending_request": True
                    if TimesheetRequest.objects.filter(project__consultant=consultant, status='request') else False,
                    "ts_status": {
                        "submitted": True if ts_qs.filter(status__in=['submitted', 'updated']) else False,
                        "rejected_ts": True if ts_qs.filter(status='rejected', is_active=True) else False,
                        "draft_ts": True if ts_qs.filter(status='draft', is_active=True) else False
                    },
                    "project": {
                        'id': obj.id,
                        'team': obj.employer,
                        'start_date': obj.start_date,
                        'client': obj.submission.client,
                        'vendor': obj.submission.lead.vendor_company.name,
                        'project_type': obj.submission.get_work_type_display(),
                        'status': timesheet_status if timesheet_status else ts_status
                    }
                }
                result.append(data)

            return Response({"data": result, 'total': len(project_qs)}, status=200)
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
                    create_notification_and_send_push(timesheet, request, "rejected")
                    serializer = self.serializer_class(timesheet)
                else:
                    create_notification_and_send_push(timesheet, request, "Approved")
                    serializer = self.serializer_class(timesheet)
                return Response({"data": serializer.data, "message": "Timesheet is updated"}, status=202)
            return Response({"message": "You don't have access"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

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


# Route - /finance/<consultant_id>/leave/
class LeaveManagementViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        consultant_id = kwargs.get('consultant_id')

        try:
            end = request.GET.get('end')
            # year = request.GET.get('year')
            start = request.GET.get('start')
            status = request.GET.get('status')
            leave_type = request.GET.get('leave_type')
            consultant = get_object_or_404(Consultant, id=consultant_id)
            queryset = self.queryset.filter(consultant=consultant).order_by('-created')
            # if year:
            #     queryset = queryset.filter(leave_type__year=year)
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


# Route - /timesheet_event/
class TimetrackEventViewSet(GenericViewSet, CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
                            DestroyModelMixin):
    queryset = TimetrackEvent.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TimetrackEventSerializer
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
    serializer_class = ConsultantRevisionViewSetSerializer

    @list_rate_revision
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
