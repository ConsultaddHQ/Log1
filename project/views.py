import json
from datetime import datetime, date

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import F, Q, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin

from constance import config
from marketing.utils import date_filter
from utils_app.models import MapMail, ObjectGroup
from utils_app.mailing import send_email
from api_key.permissions import HasAPIKey
from activity.views import create_activity
from marketing.models import Submission, User
from attachment.models import create_attachment
from utils_app.aws_utils import download_s3_object
from consultant.models import ConsultantPOC, Consultant
from notification.models import Notification, FCMDevice
from utils_app.utils import delete_temp_file, export_to_csv
from utils_app.thred_mail import send_email as send_email_, send_email_attachment_multiple, send_mail_in_thread

from log1.utils import DONT_HAVE_ACCESS, ERROR_MSG, get_time_filter, get_page_limits, write_exception
from notification.utils import push_notification_consultant
from project.models import Project, ProjectStatus, ProjectOrder, TimeSheet, ProjectSupport, SupportStatus
from project.utils import ProjectUtil, create_remote_consultant, set_consultant_password, get_attachment_status, \
    fetch_project_status, create_checklist, diff_month_days, support_assignment_mail
from project.serializers import ProjectSerializer, ProjectGetSerializer, ProjectOrderSerializer, FinanceSerializer, \
    ProjectSupportSerializer, ConsultantTimeSheetSerializer


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
                'to': [project.consultant.email], 'cc': [config.FINANCE], 'bcc': ['shreyas.k@consultadd.com'],
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
            cc = [config.RECRUITMENT, config.RELATIONS, submission.created_by.team.email, submission.created_by.email]
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
        support_res, support_msg = self.send_support_mail(project, scrum_masters, request)
        offer_res, offer_msg = self.send_offer_received_mail(project, scrum_masters, request)
        engineer = get_object_or_404(User, employee_id=request.data['engineer']) \
            if request.data.get('engineer', None) else None
        if engineer:
            support = get_object_or_404(ProjectSupport, project=project, support=engineer)
            support_assignment_mail(support, request)
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
        url = ""
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_for = request.GET.get('filter_for', None)
        filter_json = request.GET.get('filter_json', None)
        export = json.loads(request.GET.get('export', 'false'))
        filter_by_time = request.GET.get('filter_by_time', None)
        filter_by_lead = request.GET.get('filter_by_lead', None)
        filter_by_status = request.GET.get('filter_by_status', None)

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

            if filter_json:
                filters = json.loads(filter_json)

                if 'remote' in filters:
                    projects = projects.filter(is_remote=filters['remote'])

                if 'client' in filters and len(filters["client"]) > 0:
                    projects = projects.filter(submission__client=filters['client'])

                if 'w2' in filters:
                    projects = projects.filter(submission__lead__is_w2=filters['w2'])

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    projects = projects.filter(submission__created_by_id__in=filters['marketer'])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    projects = projects.filter(submission__lead__vendor_company_id__in=filters['vendor'])

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    projects = projects.filter(
                        Q(submission__consultant_marketing__consultant_id__in=filters['consultant']) |
                        Q(consultant_id__in=filters['consultant'])
                    )

                created = filters.get('created', None)
                projects = date_filter(projects, created, 'created')

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

                if 'status' in filters and len(filters["status"]) > 0:
                    not_joined = Project.objects.none()
                    if 'not_joined' in filters["status"]:
                        not_joined = projects.filter(
                            statuses__status='on_boarded', statuses__is_current=True, start_date__lt=date.today()
                        )
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

            if filter_json:
                # count of project by status
                if sort_by in ['created', 'modified']:
                    order_by = f"-{sort_by}"
                elif sort_by == 'consultant':
                    order_by = '-submission__consultant_marketing__consultant__name'
                else:
                    order_by = '-modified'

                projects = Project.objects.filter(id__in=projects.values('id')).order_by(order_by)
            if export:
                first, last = 0, len(projects)
            serializer = self.serializer_class(projects[first:last], many=True)
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
                {"name": "status", "display_name": "Status"}
            ]
            if export:
                url = export_to_csv(
                    serializer.data, col_name, f"po_{datetime.now().strftime('%d-%B-%Y')}.csv", request
                )
            return Response({"counts": data_count, "data": serializer.data, "file_url": url}, status=200)
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

                # Creating Project training Checklist
                create_checklist(project.id, request)

                # Activity
                desc = f"Purchase order created with start date of {project.start_date} and support mail is sent"
                create_activity(sub.id, 'submission', request.user, desc, 'created')

                # Assign Support Person
                engineer = get_object_or_404(User, employee_id=request.data['engineer']) \
                    if request.data.get('engineer', None) else None
                if engineer:
                    support = ProjectSupport.objects.create(
                        project=project, start=project.start_date, support=engineer
                    )
                    SupportStatus.objects.create(
                        frequency='active', support=support, is_current=True
                    )
                    desc = f"{request.user.employee_name} added {engineer.employee_name} as support person while " \
                           f"creating PO"
                    create_activity(project.id, 'projectsupport', request.user, desc, 'created')
                    # support_assignment_mail(support, request)
                message, error_msg = self.send_support_offer_mail(project, self.fetch_scrum_masters(request), request)
                serializer = self.serializer_class(project)
                return Response({"message": message, "data": serializer.data, "exception": error_msg}, status=201)
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
                    util.create_timesheet()

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

            # Activity
            if prev_rate != project.rate:
                desc = f"Purchase order rate is updated"
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
            elif prev_start_date != project.start_date:
                desc = f"Purchase order start_date is updated"
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
            else:
                create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
            serializer = self.serializer_class(project)
           
            return Response({"data": serializer.data, "error": err, "message": "Project updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

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

    def create(self, request, *args, **kwargs):
        try:
            is_proxy_support = request.data.get('is_proxy_support', False)
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
            support_person = get_object_or_404(User, id=request.data.get('support', None))
            supports = project.support.filter(end=None, is_proxy_support=False)

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

            support_qs = project.support.exists()
            project_support = ProjectSupport.objects.create(
                project=project, is_proxy_support=request.data.get('is_proxy_support', False),
                support=support_person, start=start, end=end, feedback=request.data.get('feedback', None),
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

            if not support_qs:
                message, exception_msg = support_assignment_mail(project_support, request)
                if exception_msg != 'Mail sent':
                    return Response(
                        {"exception": exception_msg, "message": "Unable to send support assignment mail"}, status=400
                    )
            return Response({"message": "Support is added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

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

    @action(methods=['put'], detail=True, url_path="update_details")
    def details(self, request, project_id, pk):
        try:
            msg = {}
            data = request.data
            support = get_object_or_404(ProjectSupport, id=pk, project_id=project_id)
            prev_support = support.statuses.filter(is_current=True).first()

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

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=request.GET.get('project_id'))
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
        end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))

        try:
            projects = Project.objects.filter(
                Q(statuses__is_current=True, consultant_id=kwargs.get('pk', None)) & (
                        Q(statuses__status__istartswith='terminated') |
                        Q(statuses__status='complete') | Q(statuses__status='joined')
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

                    new_timesheet = TimeSheet.objects.create(
                        remark=timesheet.remark, project=timesheet.project,
                        status='rejected', start=timesheet.start, end=timesheet.end,
                        additional_hours=timesheet.additional_hours, hours=timesheet.hours,
                    )
                    sender_content_type = ContentType.objects.get(model='user')
                    target_content_type = ContentType.objects.get(model='timesheet')
                    recipient_content_type = ContentType.objects.get(model='consultant')

                    if new_timesheet.remark or len(new_timesheet.remark) != 0:
                        title = f"Timesheet rejected for week end {str(new_timesheet.end)} for client " \
                                f"{new_timesheet.project.submission.client} \n Remark: {new_timesheet.remark}"
                    else:
                        title = f"Timesheet rejected for week end {str(new_timesheet.end)} for client " \
                                f"{new_timesheet.project.submission.client}"

                    Notification.objects.create(
                        category="rejected", recipient_content_type=recipient_content_type,
                        title=title, recipient_object_id=new_timesheet.project.consultant.id,
                        sender_content_type=sender_content_type, target_content_type=target_content_type,
                        description=title, target_object_id=new_timesheet.id, sender_object_id=request.user.id,
                    )

                    # Push Notification
                    message_body = {
                        "body": title, "title": title, "category": "rejected",
                        "show_in_foreground": True, "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "data": {
                            'target': 'timesheet', 'target_id': new_timesheet.id,
                            'is_read': False, 'is_deleted': False, 'timestamp': str(timezone.now()),
                        },
                    }
                    object_ids = new_timesheet.project.consultant.consultant_token.all().values_list('key', flat=True)
                    registration_ids = list(
                        FCMDevice.objects.filter(
                            object_id__in=list(object_ids), content_type__model='consultanttoken'
                        ).values_list('device_id', flat=True))
                    push_notification_consultant(registration_ids, message_body)
                    serializer = self.serializer_class(new_timesheet)
                else:
                    serializer = self.serializer_class(timesheet)
                return Response({"data": serializer.data, "message": "Timesheet is updated"}, status=202)
            return Response({"message": "You don't have access"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=["get"], detail=True, url_name="from_notification")
    def from_notification(self, request, pk):
        try:
            queryset = TimeSheet.objects.filter(id=pk)
            serializer = self.serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
