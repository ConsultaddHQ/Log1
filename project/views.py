import os
import logging
from datetime import datetime, date, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin

from constance import config
from project.serializers import *
from api_key.permissions import HasAPIKey
from consultant.models import ConsultantPOC, Consultant
from marketing.models import Submission, User
from attachment.views import download_s3_object, delete_temp_file
from utils_app.utils import get_time_filter, post_msg_using_webhook
from notification.views import push_notification, Notification, FCMDevice
from utils_app.mailing import send_email_attachment_multiple, send_email

logger = logging.getLogger(__name__)


class ProjectViewSets(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def consultant_mail_on_joining(self, project, password, link):
        try:
            mail_data = {
                'to': [project.consultant.email],
                'cc': [],
                'bcc': ['sarang.m@consultadd.com'],
                'template': '../templates/consultant_account_creation.html',
                'subject': f'Your account created on Consultadd Time Track App',
                'context': {
                    'iphone_link': link,
                    'password': password,
                    'tutorial_video': config.TUTORIAL_VIDEO,
                    'android_link': config.ANDROID_APP_LINK,
                    'consultant_name': project.consultant.name,
                    'consultant_email': project.consultant.email,
                },
            }
            res = send_email(mail_data, config.RELATIONS)
            return res, "ok"
        except Exception as error:
            logger.error(error)
            return error, "error"

    def send_offer_received_mail(self, project, submission, scrum_master):
        try:
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, submission.created_by.email,
                  submission.created_by.team.email]

            cc = [config.SUPERADMIN]

            recruiter = project.consultant.recruiter
            retention = project.consultant.relation
            if recruiter:
                cc.append(recruiter.email)

            if retention:
                cc.append(retention.email)

            if scrum_master:
                cc.append(scrum_master)

            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': f'Offer Received of {project.consultant.name} :: {submission.client} :: '
                           f'{str(project.start_date)} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/offer.html',
                'context': {
                    'start': project.start_date,
                    'rate': int(submission.rate),
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'con_rate': project.consultant.rate,
                    'job_title': submission.lead.job_title,
                    'vendor_company': submission.vendor.name,
                    'consultant_name': project.consultant.name,
                    'consultant_email': project.consultant.email,
                    'marketer_name': submission.created_by.employee_name,
                },
            }
            res = send_email(mail_data, submission.created_by.email)
            return res, "ok"
        except Exception as error:
            logger.error(error)
            return error, "error"

    def support_mail(self, project, submission, scrum_master):
        try:
            path, recordings = [], []
            resume = submission.attachments.filter(attachment_type='resume')

            recordings = [interview.attachment_link for interview in submission.screening.all()
                          if interview.attachment_link is not None]
            recordings = ", ".join(recordings) if len(recordings) != 0 else "NA"

            if resume:
                path.append(download_s3_object(resume.first().attachment_file.name))

            recruiter = project.consultant.recruiter
            retention = project.consultant.relation
            cc = [config.RECRUITMENT, config.RELATIONS, submission.created_by.email, submission.created_by.team.email]

            if recruiter:
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            if scrum_master:
                cc.append(scrum_master)

            consultant_name = project.consultant.name
            mail_data = {
                'to': [config.ENGINEERING],
                'cc': cc,
                'bcc': [],
                'subject': f'Support Initiation for {consultant_name} {submission.client} {submission.lead.city}',
                'template': '../templates/support.html',
                'context': {
                    'recordings': recordings,
                    'start': project.start_date,
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'location': submission.lead.city,
                    'consultant_name': consultant_name,
                    'job_title': submission.lead.job_title,
                    'consultant_email': project.consultant.email,
                    'consultant_phone_no': project.consultant.phone_no,
                    'marketer_name': submission.created_by.employee_name,
                    'consultant_location': project.consultant.current_city,
                    'jd': submission.lead.job_desc.replace("\n", " ;newline; "),
                },
                'attachments': path
            }
            res = send_email_attachment_multiple(mail_data, submission.created_by.email)
            delete_temp_file(path)
            logger.error("Support mail res for {}".format(submission.created_by.email), res)
            return res, "ok"
        except Exception as error:
            logger.error("Support mail exception error for {}".format(submission.created_by.email), error)
            return error, "error"

    def po_mail(self, project, path, scrum_master_email, po_type):
        submission = project.submission
        marketer = submission.created_by
        try:
            vendor_contact = submission.vendor_contact
            if not vendor_contact:
                return "Vendor is empty", 'error'

            recruiter = project.consultant.recruiter
            retention = project.consultant.relation
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL, marketer.team.email]

            if recruiter:
                to.append(recruiter.email)
            if retention:
                to.append(retention.email)

            cc = [marketer.email, config.SUPERADMIN]
            if scrum_master_email:
                cc.append(scrum_master_email)

            consultant_name = project.consultant.name
            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': f'On Boarding of {consultant_name} :: {submission.employer} :: '
                           f'{str(project.start_date)} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/po.html',
                'context': {
                    'type': po_type,
                    'rate': submission.rate,
                    'start': project.start_date,
                    'client_name': submission.client,
                    'vendor_name': vendor_contact.name,
                    'consultant_name': consultant_name,
                    'vendor_email': vendor_contact.email,
                    'payment_term': project.payment_term,
                    'job_title': submission.lead.job_title,
                    'vendor_number': vendor_contact.number,
                    'employer': submission.employer.title(),
                    'client_address': project.client_address,
                    'vendor_address': project.vendor_address,
                    'con_rate': int(project.consultant.rate),
                    'consultant_email': project.consultant.email,
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
            logger.error("Offer mail error for {}".format(marketer.email), error)
            return error, "error"

    def po_termination_or_cancellation_mail(self, project, scrum_master_email, po_type):
        submission = project.submission
        marketer = submission.created_by
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

            recruiter = project.consultant.recruiter
            retention = project.consultant.relation

            if recruiter:
                to.append(recruiter.email)
            if retention:
                to.append(retention.email)

            cc = [marketer.email, config.SUPERADMIN]

            if scrum_master_email:
                cc.append(scrum_master_email)
            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': f'{po_type} of {project.consultant.name} :: {submission.employer} ::'
                           f' {str(project.start_date)} :: {submission.client} :: {submission.vendor.name}',
                'template': '../templates/po_termination.html',
                'context': {
                    'end': project.end_date,
                    'rate': submission.rate,
                    'remark': project.feedback,
                    'start': project.start_date,
                    'vendor_name': vendor_name,
                    'vendor_email': vendor_email,
                    'vendor_number': vendor_number,
                    'client_name': submission.client,
                    'job_title': submission.lead.job_title,
                    'employer': submission.employer.title(),
                    'marketer_name': marketer.employee_name,
                    'vendor_address': project.vendor_address,
                    'client_address': project.client_address,
                    'consultant_name': project.consultant.name,
                    'consultant_email': project.consultant.email,
                    'reporting_details': project.reporting_details,
                    'vendor_company': submission.lead.vendor_company.name,
                    'reason': project.statuses.get(is_current=True).get_status_display(),
                }
            }
            res = send_email(mail_data, marketer.email)
            return res, "ok"
        except Exception as error:
            logger.error("Offer mail error for {}".format(marketer.email), error)
            return error, "error"

    @action(methods=['get'], detail=False, url_path="mail_to_onboard")
    def mail_to_onboard(self, request):
        try:
            project_id = request.query_params.get('project_id', None)
            if project_id:

                project = get_object_or_404(Project, id=project_id)

                client_address, vendor_address, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0

                start_date = 1 if project.start_date else 0

                if project.attachments.filter(attachment_type='msa_signed'):
                    s_msa = 1

                if project.attachments.filter(attachment_type='work_order_signed'):
                    s_work_order = 1

                if project.attachments.filter(attachment_type='work_order_msa_signed'):
                    s_msa, s_work_order = 1, 1

                if project.client_address and len(project.client_address.strip()) > 0:
                    client_address = 1

                if project.vendor_address and len(project.vendor_address.strip()) > 0:
                    vendor_address = 1

                if project.reporting_details and len(project.reporting_details.strip()) > 0:
                    reporting_details = 1

                list_status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                                       + reporting_details) / 6 >= 1 else False

                if not list_status:
                    return Response({"error": "Complete all details"}, status=status.HTTP_400_BAD_REQUEST)

                prev_status = project.statuses.filter(is_current=True).first()
                po_type = 'created'
                if prev_status.status == 'on_boarded':
                    po_type = 'updated'

                path = []
                scrum_master_email = None
                scrum_master = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
                if scrum_master:
                    scrum_master_email = scrum_master.first().email

                for i in project.attachments.filter(
                        attachment_type__in=['work_order_signed', 'work_order_msa_signed', 'msa_signed']):
                    path.append(download_s3_object(i.attachment_file.name))

                res, error = self.po_mail(project, path, scrum_master_email, po_type)
                if not error == 'error':
                    delete_temp_file(path)
                    project.submission.consultant_marketing.status = 'close'
                    project.submission.consultant_marketing.save()
                    if prev_status.status == 'received':
                        new_status, created = ProjectStatus.objects.get_or_create(
                            project=project,
                            is_current=True,
                            status='on_boarded',
                        )
                        if created:
                            prev_status.is_current = False
                            prev_status.save()
                    return Response({"result": "mail sent", "message": res}, status=status.HTTP_200_OK)
                return Response({"result": str(res)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Invalid Id"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            serializer = ProjectGetSerializer(project)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        filter_for = request.query_params.get('filter_for', None)
        filter_by_time = request.query_params.get('filter_by_time', None)
        filter_by_status = request.query_params.get('filter_by_status', None)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            # search project by client and consultant
            if filter_for == 'my':
                projects = Project.objects.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                projects = Project.objects.filter(submission__created_by__team=request.user.team)
            else:
                projects = Project.objects.all()

            if query:
                projects = projects.filter(
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query)
                )

            if filter_by_time:
                projects = get_time_filter(projects, filter_by_time)

            # count of project by status
            projects = projects.order_by('-modified').distinct('modified')
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
            serializer = self.serializer_class(projects[first:last], many=True)
            return Response({"results": serializer.data, "counts": data_count}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        sub_id = request.data.get('submission')
        try:
            sub = get_object_or_404(Submission, id=sub_id, created_by=request.user)
            if hasattr(sub, 'project'):
                return Response({"error": "Project already exist"}, status=status.HTTP_406_NOT_ACCEPTABLE)

            serializer = self.serializer_class(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                project = Project.objects.get(id=serializer.data['id'])
                ProjectStatus.objects.create(
                    status='new',
                    project=project,
                    is_current=True
                )

                sub.status = 'project'
                sub.save()

                project.city = sub.lead.city
                project.consultant = sub.consultant
                project.save()

                queryset = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'], is_active=True)
                scrum_masters = [{"email": user.email} for user in queryset]

                support_mail_res = "Development Server"
                offer_mail_res = "Development Server"

                if os.environ.get('ENV', 'local') == 'prod':
                    support_mail_res, support_mail_error = self.support_mail(project, sub, scrum_masters)
                    offer_mail_res, offer_mail_error = self.send_offer_received_mail(project, sub, scrum_masters)
                    if support_mail_error == 'error' or offer_mail_error == 'error':
                        logger.error(support_mail_res)
                        logger.error(offer_mail_res)
                        return Response({"error": "error", "support_mail_error": str(support_mail_res),
                                         "offer_mail_error": offer_mail_error}, status=status.HTTP_400_BAD_REQUEST)

                return Response({
                    "result": serializer.data,
                    "support_mail": str(support_mail_res),
                    "offer_mail": str(offer_mail_res)
                }, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            err = None
            new_status = request.data.get('status', None)
            project = get_object_or_404(Project, id=project_id)
            prev_status_obj = project.statuses.get(is_current=True)

            data = {
                "city": request.data.get('city', None),
                "duration": request.data.get('duration', None),
                "end_date": request.data.get('end_date', None),
                "feedback": request.data.get('feedback', None),
                "start_date": request.data.get('start_date', None),
                "payment_term": request.data.get('payment_term', None),
                "client_address": request.data.get('client_address', None),
                "vendor_address": request.data.get('vendor_address', None),
                "invoicing_period": request.data.get('invoicing_period', None),
                "reporting_details": request.data.get('reporting_details', None),
            }
            if data["city"]:
                project.city = data["city"]
            if data["duration"]:
                project.duration = data["duration"]
            if data["end_date"]:
                project.end_date = data["end_date"]
            if data["feedback"]:
                project.feedback = data["feedback"]
            if data["start_date"]:
                project.start_date = data["start_date"]
            if data["payment_term"]:
                project.payment_term = data["payment_term"]
            if data["client_address"]:
                project.client_address = data["client_address"]
            if data["vendor_address"]:
                project.vendor_address = data["vendor_address"]
            if data["invoicing_period"]:
                project.invoicing_period = data["invoicing_period"]
            if data["reporting_details"]:
                project.reporting_details = data["reporting_details"]

            project.save()

            # Emoji for Mattermost update
            if project.consultant.recruiter:
                recruiter_gender_emoji = ':pouting_woman: ' if project.consultant.recruiter.gender == 'female' else ':man_office_worker: '
            else:
                recruiter_gender_emoji = ':man_office_worker: '

            client_emoji = ':tophat: '
            role_emoji = ':fist_oncoming: '
            employer_emoji = ':briefcase: '
            marketer_gender_emoji = ':blonde_woman: ' if project.submission.created_by.gender == 'female' else ':blonde_man: '
            consultant_gender_emoji = ':woman: ' if project.consultant.gender == 'female' else ':man: '

            # For Status Change
            prev_statuses = list(project.statuses.all().values_list('status', flat=True))
            if new_status not in prev_statuses:
                p_status, p_s_created = ProjectStatus.objects.get_or_create(
                    status=new_status.lower(),
                    is_current=True,
                    project=project
                )
                if p_s_created:
                    prev_status_obj.is_current = False
                    prev_status_obj.save()

                # If status is Joined
                if new_status.startswith('cancelled'):
                    project.submission.consultant_marketing.status = 'open'
                    project.submission.consultant_marketing.save()

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
                        submission__employer__iexact=project.submission.employer,
                    ).count()

                    # Sending message on Mattermost on joined status
                    data = {
                        "response_type": "in_channel",
                        "username": "Log1 Updates",
                        "text": f"""
#### Project Joined :metal: :smile: :metal:\n
{consultant_gender_emoji} Consultant :  ** {project.consultant.name} **
{marketer_gender_emoji} Marketer :   {project.marketer_name}
{recruiter_gender_emoji} Recruiter :   {project.consultant.recruiter.employee_name}
{employer_emoji} Employer :   {project.submission.employer.title()}
:us: Location: {project.city}
{client_emoji} Client :  {project.submission.client}
{role_emoji} Role :  {project.submission.lead.job_title}
:spiral_calendar: Joining Date :   {str(project.start_date)}\n\n
`Project Joined count of {project.submission.employer} for this month - {team_joined_count} `
`Total Project Joined count of this month - {total_joined_count}`
"""
                    }
                    post_msg_using_webhook(config.joined_url, data)

                    consultant = project.consultant
                    if not consultant.work_type == 'w2':
                        # Creating first week Timesheet on project status change to joined
                        start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d')
                        week_day = start_date.weekday()
                        if week_day == 6:
                            end_date = start_date + timedelta(days=6)
                        else:
                            end_date = start_date + timedelta(days=5 - week_day)

                        TimeSheet.objects.get_or_create(
                            hours=0,
                            end=end_date,
                            status='draft',
                            project=project,
                            start=start_date,
                        )

                        if not IphoneAppLink.objects.filter(is_sent=True, consultant=consultant):
                            password = config.CONSULTANT_PASSWORD
                            consultant.set_password(password)
                            consultant.is_active = True
                            consultant.save()

                            if os.environ.get('ENV', 'local') == 'prod':
                                links = IphoneAppLink.objects.filter(is_sent=False)
                                if links:
                                    link = links.first()
                                    iphone_link = link.link
                                    resp, err = self.consultant_mail_on_joining(project, password, iphone_link)
                                    if err == 'ok':
                                        link.is_sent = True
                                        link.sent_on = datetime.now()
                                        link.consultant = consultant
                                        link.save()

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
                        submission__employer__iexact=project.submission.employer,
                    ).count()

                    interviews = project.submission.screening.exclude(status='cancelled')
                    ctb_gender = interviews.last().supervisor.gender
                    supervisors = "\n".join(
                        [f"-    Round {interview.round} - {interview.supervisor.employee_name}\n" for
                         interview in
                         interviews if interview.supervisor])
                    ctb_gender_emoji = ':raising_hand_woman: ' if ctb_gender == 'female' else ':raising_hand_man: '

                    # Sending message on Mattermost
                    data = {
                        "response_type": "in_channel",
                        "username": "Log1 Updates",
                        "text": f"""
#### Offer :metal: :smile: :metal:\n
{consultant_gender_emoji} Consultant :  ** {project.consultant.name} **
{marketer_gender_emoji} Marketer :   {project.marketer_name}
{recruiter_gender_emoji} Recruiter :   {project.consultant.recruiter.employee_name}
{employer_emoji} Employer :   {project.submission.employer.title()}
{ctb_gender_emoji} CTB :
{supervisors}
:us: Location: {project.city}
{client_emoji} Client :  {project.submission.client}
{role_emoji} Role :  {project.submission.lead.job_title}
:spiral_calendar: Start Date :   {str(project.start_date)}\n\n
`Offer count of {project.submission.employer} for this month - {team_offer_count} `
`Total offer count of this month - {total_offer_count}`
"""
                    }
                    post_msg_using_webhook(config.offer_url, data)
                    project.is_msg_sent = True
                    project.save()

                # Mail for Cancellation or Termination of Project
                cancellation_status = ['cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled',
                                       'cancelled-contract_conflicts', 'cancelled-candidate_denied',
                                       'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
                                       'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location']
                termination_status = ['terminated', 'terminated-resigned', 'terminated-fired',
                                      'terminated-resigned_rate_issue', 'terminated-resigned_technology_issue',
                                      'terminated-fired_budget_issue', 'terminated-fired_security_issue',
                                      'terminated-resigned_location_issue', 'terminated-fired_performance_issue',
                                      'terminated-resigned_full_time_offer']

                if os.environ.get('ENV', 'local') == 'prod':
                    scrum_master = None
                    queryset = User.objects.filter(team=request.user.team, role__name='admin')
                    if queryset:
                        scrum_master = queryset.first().email

                    if prev_status_obj.status not in termination_status and new_status in termination_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_master, 'PO Termination')
                        project.consultant.status = 'on_bench'
                        project.consultant.save()

                    elif prev_status_obj.status not in cancellation_status and new_status in cancellation_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_master, 'PO Cancellation')

                        text = f"""#### Offer Feedback \n"""
                        text += f"""{consultant_gender_emoji} Consultant :  ** {project.consultant.name} **
{marketer_gender_emoji} Marketer :   {project.marketer_name}
{recruiter_gender_emoji} Recruiter :   {project.consultant.recruiter.employee_name}
{employer_emoji} Employer :   {project.submission.employer.title()}
:us: Location: {project.city}
{client_emoji} Client :  {project.submission.client}
{role_emoji} Role :  {project.submission.lead.job_title}
:spiral_calendar: Joining Date :   {str(project.start_date)}\n\n"""

                        text += "**Reason: **" + project.feedback

                        data = {
                            "response_type": "in_channel",
                            "username": "Log1 Updates",
                            "text": text,
                        }
                        post_msg_using_webhook(config.offer_failure_url, data)

                    elif prev_status_obj.status != 'complete' and new_status == "complete":
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_master, 'PO Completion')

            serializer = self.serializer_class(project)

            return Response({"result": serializer.data, "error": err}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class EngineeringProjectsViewSets(viewsets.GenericViewSet, ListModelMixin):
    authentication_classes = ()
    permission_classes = (HasAPIKey,)
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

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
                employer=F('submission__employer'),
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

            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(str(error))
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)


class FinanceTimeSheetViewSets(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', date.today())

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            projects = Project.objects.filter(
                statuses__is_current=True,
                statuses__status='joined',
                consultant_id=kwargs.get('pk', None),
            )
            if projects:
                project = projects.latest('id')
                if start:
                    queryset = TimeSheet.objects.filter(
                        project=project, start__range=[start, end]
                    ).exclude(status='draft')
                else:
                    queryset = TimeSheet.objects.filter(project=project).exclude(status='draft')
                total = queryset.count()
                serializer = self.serializer_class(queryset[first:last], many=True)
                return Response({"results": serializer.data, 'total': total}, status=status.HTTP_200_OK)
            return Response({"error": "No Project Found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        query = request.query_params.get('query', None)
        consultant_id = request.query_params.get('consultant', None)
        consultant_name = request.query_params.get('consultant_name', None)

        try:

            project_status = ['joined', 'terminated-resigned', 'terminated', 'terminated-resigned_location_issue',
                              'terminated-resigned_location_issue', 'terminated-resigned_full_time_offer',
                              'terminated-resigned_technology_issue', 'terminated-fired_budget_issue',
                              'terminated-fired_performance_issue', 'terminated-fired_security_issue']

            if consultant_id:
                consultants = Consultant.objects.filter(id=consultant_id).exclude(status='archived')
            elif consultant_name:
                consultants = Consultant.objects.filter(name__istartswith=consultant_name)
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
                consultants = Consultant.objects.filter(
                    Q(name__istartswith=query) |
                    Q(projects__submission__client__icontains=query) |
                    Q(projects__submission__employer__startswith=query) |
                    Q(projects__submission__lead__vendor_company__name__icontains=query)
                ).order_by('id').distinct('id')

            queryset = consultants.order_by('name').distinct('name')
            total = queryset.count()
            serializer = ConsultantTimeSheetSerializer(queryset[first:last], many=True)
            return Response({"results": serializer.data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                        status='draft',
                        end=timesheet.end,
                        start=timesheet.start,
                        remark=timesheet.remark,
                        project=timesheet.project,
                    )
                    recipient_content_type = ContentType.objects.get(model='consultant')
                    sender_content_type = ContentType.objects.get(model='user')
                    target_content_type = ContentType.objects.get(model='timesheet')

                    Notification.objects.create(
                        title=f"Timesheet rejected for week end {str(timesheet.end)}",
                        category="rejected",
                        target_object_id=timesheet.id,
                        sender_object_id=request.user.id,
                        sender_content_type=sender_content_type,
                        target_content_type=target_content_type,
                        recipient_content_type=recipient_content_type,
                        recipient_object_id=timesheet.project.consultant.id,
                        description=f"Timesheet rejected for week end {str(timesheet.end)}",
                    )

                    # Push Notification
                    message_body = {
                        "category": "rejected",
                        "show_in_foreground": True,
                        "title": f"Timesheet rejected for week end {str(timesheet.end)}",
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "body": f"Timesheet rejected for week end {str(timesheet.end)}",
                        "data": {
                            'is_read': False,
                            'is_deleted': False,
                            'target_id': timesheet.id,
                            'timestamp': str(timezone.now()),
                        },
                    }
                    object_ids = timesheet.project.consultant.consultant_token.all().values_list('key', flat=True)
                    registration_ids = list(
                        FCMDevice.objects.filter(object_id__in=list(object_ids), content_type__model='consultanttoken'
                                                 ).values_list('device_id', flat=True))
                    push_notification(registration_ids, message_body)
                serializer = self.serializer_class(timesheet)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            return Response({"error": "You don't have access"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=True, url_name="from_notification")
    def from_notification(self, request, *args, **kwargs):
        try:
            queryset = TimeSheet.objects.filter(id=kwargs.get('pk'))
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
