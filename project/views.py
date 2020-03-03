import os
import logging
from datetime import datetime, date

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Subquery, OuterRef

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
from consultant.models import ConsultantPOC
from marketing.models import Submission, User
from utils_app.utils import get_time_filter, post_msg_using_webhook
from utils_app.mailing import send_email_attachment_multiple, send_email

logger = logging.getLogger(__name__)


class ProjectViewSets(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)
    get_serializer_class = ProjectGetSerializer
    create_serializer_class = ProjectGetSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def send_offer_received_mail(self, submission, scrum_master):
        try:
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, submission.created_by.email,
                  submission.created_by.team.email]

            cc = config.SUPERADMIN

            recruiter = submission.consultant.recruiter
            retention = submission.consultant.relation
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
                'subject': 'Offer Received of {} :: {} :: {} :: {} :: {}'.format(
                    submission.consultant.name, submission.client, str(self.start_date), submission.client,
                    submission.vendor.name
                ),
                'template': '../templates/offer.html',
                'context': {
                    'start': self.start_date,
                    'rate': int(submission.rate),
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'marketer_name': submission.marketer,
                    'job_title': submission.lead.job_title,
                    'con_rate': submission.consultant.rate,
                    'vendor_company': submission.vendor.name,
                    'consultant_name': submission.consultant.name,
                    'consultant_email': submission.consultant.email,
                },
            }
            res = send_email(mail_data, submission.created_by.email)
            return res, "ok"
        except Exception as error:
            logger.error(error)
            return error, "error"

    @staticmethod
    def support_mail(self, start_date, submission, scrum_master):
        try:
            path, recordings = [], []
            resume = submission.attachments.filter(attachment_type='resume')

            recordings = [interview.attachment_link for interview in submission.screening.all()
                          if interview.attachment_link is not None]
            recordings = ", ".join(recordings) if len(recordings) != 0 else "NA"

            if resume:
                path.append(resume.first().attachment_file.path)

            recruiter = submission.consultant.recruiter
            retention = submission.consultant.relation
            cc = [config.RECRUITER, config.RELATIONS, submission.created_by.email, submission.created_by.team.email]

            if recruiter:
                cc.append(recruiter.email)
            if retention:
                cc.append(retention.email)

            if scrum_master:
                cc.append(scrum_master)

            consultant_name = submission.consultant.name
            mail_data = {
                'to': [config.ENGINEERING],
                'cc': cc,
                'bcc': [],
                'subject': 'Support Initiation for {} {} {}'.format(
                    consultant_name, submission.client, submission.lead.city
                ),
                'template': '../templates/support.html',
                'context': {
                    'start': start_date,
                    'recordings': recordings,
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'location': submission.lead.city,
                    'consultant_name': consultant_name,
                    'job_title': submission.lead.job_title,
                    'consultant_email': submission.consultant.email,
                    'marketer_name': submission.created_by.employee_name,
                    'consultant_phone_no': submission.consultant.phone_no,
                    'jd': submission.lead.job_desc.replace("\n", " ;newline; "),
                },
                'attachments': path
            }
            res = send_email_attachment_multiple(mail_data, submission.created_by.email)
            logger.error("Support mail res for {}".format(submission.created_by.email), res)
            return res, "ok"
        except Exception as error:
            logger.error("Support mail exception error for {}".format(submission.created_by.email), error)
            return error, "error"

    @staticmethod
    def po_mail(self, path, scrum_master_email, po_type):
        marketer = self.submission.created_by
        try:
            vendor_contact = self.submission.vendor_contact
            if not vendor_contact:
                return "Vendor is empty", 'error'

            recruiter = self.submission.consultant.recruiter
            retention = self.submission.consultant.relation
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL, marketer.team.email]

            if recruiter:
                to.append(recruiter.email)
            if retention:
                to.append(retention.email)

            cc = [marketer.email] + config.SUPERADMIN
            if scrum_master_email:
                cc.append(scrum_master_email)

            consultant_name = self.submission.consultant.name
            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': f'On Boarding of {consultant_name} :: {self.submission.employer} :: '
                           f'{str(self.start_date)} :: {self.submission.client} :: {self.submission.vendor.name}',
                'template': '../templates/po.html',
                'context': {
                    'type': po_type,
                    'start': self.start_date,
                    'rate': self.submission.rate,
                    'payment_term': self.payment_term,
                    'vendor_name': vendor_contact.name,
                    'consultant_name': consultant_name,
                    'vendor_email': vendor_contact.email,
                    'client_address': self.client_address,
                    'client_name': self.submission.client,
                    'vendor_address': self.vendor_address,
                    'vendor_number': vendor_contact.number,
                    'invoicing_period': self.invoicing_period,
                    'job_title': self.submission.lead.job_title,
                    'reporting_details': self.reporting_details,
                    'employer': self.submission.employer.title(),
                    'con_rate': int(self.submission.consultant.rate),
                    'consultant_email': self.submission.consultant.email,
                    'marketer_name': self.submission.created_by.employee_name,
                    'vendor_company': self.submission.lead.vendor_company.name,
                },
                'attachments': path
            }
            res = send_email_attachment_multiple(mail_data, marketer.email)
            return res, "ok"
        except Exception as error:
            logger.error("Offer mail error for {}".format(marketer.email), error)
            return error, "error"

    @staticmethod
    def po_termination_or_cancellation_mail(self, scrum_master_email, po_type):
        marketer = self.submission.created_by
        try:
            vendor = self.submission.vendor_contact
            recruiter = self.submission.consultant.recruiter
            retention = self.submission.consultant.relation
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL, marketer.team.email]

            if recruiter:
                to.append(recruiter.email)
            if retention:
                to.append(retention.email)

            cc = [marketer.email] + config.SUPERADMIN

            if scrum_master_email:
                cc.append(scrum_master_email)
            consultant_name = self.submission.consultant_name
            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': '{} of {} :: {} :: {} :: {} :: {}'.format(
                    po_type, consultant_name, self.submission.employer, str(self.start_date), self.submission.client,
                    self.vendor),
                'template': '../templates/po_termination.html',
                'context': {
                    'end': self.end_date,
                    'remark': self.feedback,
                    'start': self.start_date,
                    'vendor_name': vendor.name,
                    'rate': self.submission.rate,
                    'vendor_email': vendor.email,
                    'vendor_number': vendor.number,
                    'vendor_address': self.vendor_address,
                    'client_address': self.client_address,
                    'client_name': self.submission.client,
                    'marketer_name': marketer.employee_name,
                    'job_title': self.submission.lead.job_title,
                    'reporting_details': self.reporting_details,
                    'employer': self.submission.employer.title(),
                    'consultant_name': self.submission.consultant.name,
                    'consultant_email': self.submission.consultant.email,
                    'vendor_company': self.submission.lead.vendor_company.name,
                    'reason': self.statuses.get(is_current=True).get_status_display(),
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
                po_type = 'created'
                if project.status == 'on_boarded':
                    po_type = 'updated'
                path = []
                scrum_master_email = None
                scrum_master = User.objects.filter(team=request.user.team, role__name='admin')
                if scrum_master:
                    scrum_master_email = scrum_master.first().email

                for i in project.attachments:
                    path.append(i.attachment_file.path)
                res = "Development server"
                error = "error"
                if os.getenv('ENV') == 'prod':
                    res, error = self.po_mail(project, path, scrum_master_email, po_type)
                if error == 'error':
                    return Response({"result": str(res)}, status=status.HTTP_400_BAD_REQUEST)
                project.status = 'on_boarded'
                project.save()

                return Response({"result": "mail sent"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid Id"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            serializer = self.get_serializer_class(project)
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
                    Q(city__istartswith=query) |
                    Q(consultant__name__istartswith=query) |
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query)
                )

            if filter_by_time:
                projects = get_time_filter(projects, filter_by_time)

            # count of project by status
            project = projects.order_by('-modified').distinct('modified')
            total = projects.count()
            new = projects.filter(statuses__status='new', statuses__is_current=True).count()
            joined = projects.filter(statuses__status='joined', statuses__is_current=True).count()
            received = projects.filter(statuses__status='received', statuses__is_current=True).count()
            on_boarded = projects.filter(statuses__status='on_boarded', statuses__is_current=True).count()
            not_joined = projects.filter(statuses__status='not_joined', statuses__is_current=True).count()

            if filter_by_status:
                project = projects.filter(statuses__status=filter_by_status, statuses__is_current=True)

            data_count = {
                'new': new,
                'total': total,
                'joined': joined,
                'received': received,
                'on_boarded': on_boarded,
                'not_joined': not_joined,
            }
            serializer = self.serializer_class(project[first:last], many=True)
            return Response({"results": serializer.data, "counts": data_count}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        sub_id = request.data.get('submission')
        try:
            sub = get_object_or_404(Submission, id=sub_id)
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
                project.consultant = sub.consultant
                project.city = sub.lead.city
                project.save()

                queryset = User.objects.filter(team=request.user.team, role__name=['admin', 'proxy'], is_active=True)
                scrum_masters = [{"email": user.email} for user in queryset]

                # support_mail_res, support_mail_error = self.support_mail(sub, scrum_masters)
                # offer_mail_res, offer_mail_error = self.send_offer_received_mail(sub, scrum_masters)
                # if support_mail_error == 'error' or offer_mail_error == 'error':
                #     logger.error(support_mail_res)
                #     logger.error(offer_mail_res)
                #     return Response({"error": "error", "support_mail_error": str(offer_mail_error),
                #                      "offer_mail_error": offer_mail_error}, status=status.HTTP_400_BAD_REQUEST)
                return Response({
                    "result": serializer.data,
                    "support_mail": "support_mail_res",
                    "offer_mail": "offer_mail_res"
                }, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            project = get_object_or_404(Project, id=project_id)
            prev_status_obj = project.statuses.get(is_current=True)
            new_status = request.data.get('status', None)

            project.city = request.data.get('city', None)
            project.duration = request.data.get('duration', None)
            project.end_date = request.data.get('end_date', None)
            project.start_date = request.data.get('start_date', None)
            project.payment_term = request.data.get('payment_term', None)
            project.client_address = request.data.get('client_address', None)
            project.vendor_address = request.data.get('vendor_address', None)
            project.invoicing_period = request.data.get('invoicing_period', None)
            project.reporting_details = request.data.get('reporting_details', None)
            project.save()

            if prev_status_obj.status != new_status:
                ProjectStatus.objects.create(
                    status=new_status,
                    is_current=True,
                    project=project
                )
                prev_status_obj.is_current = False
                prev_status_obj.save()

                if new_status == 'joined':
                    project.consultant.status = 'on_project'
                    project.consultant.save()

            serializer = self.serializer_class(project)

            day_one = datetime.today().replace(day=1, hour=0, minute=0)
            total_offer = Project.objects.filter(
                statuses__created__gte=day_one, statuses__status='new'
            ).count()

            team_offer_count = Project.objects.filter(
                statuses__created__gte=day_one, statuses__status='new',
                submission__created_by__team=request.user.team
            ).count()

            err = None
            # Cancellation or Termination Mail
            cancellation_status = ['dual-offer', 'client-cancelled', 'contract-conflicts',
                                   'candidate-absconded', 'candidate-denied-jd', 'candidate-denied-rate',
                                   'candidate-denied-location']
            termination_status = ['completed', 'resigned-rate', 'terminated-other', 'resigned-location',
                                  'resigned-full_time', 'resigned-technology', 'client-fired-budget',
                                  'client-fired-performance', 'client-fired-security']
            scrum_master = None
            queryset = User.objects.filter(team=request.user.team, role__name='admin')
            if queryset:
                scrum_master = queryset.first().email
            if prev_status_obj.status not in termination_status and new_status in termination_status:
                resp, err = self.po_termination_or_cancellation_mail(scrum_master, 'PO Termination')
            elif prev_status_obj.status not in cancellation_status and new_status in cancellation_status:
                resp, err = self.po_termination_or_cancellation_mail(scrum_master, 'PO Cancellation')

            # Discord message for PO
            if new_status == 'received' and not project.is_msg_sent:
                interviews = project.submission.screening.exclude(status='cancelled')
                supervisors = "\n".join(
                    [f"     - Round {interview.round}  {interview.supervisor.employee_name}\n" for interview in
                     interviews if interview.supervisor])

                # Sending message on Mattermost
                data = {
                    "response_type": "in_channel",
                    "username": "Log1 Updates",
                    "text": f"""
#### Offer :metal: :smile: :metal:\n
Employer :   {project.submission.employer.title()}
Marketer :   {project.marketer_name}
Consultant :   {project.consultant.name}
Recruiter :   {project.submission.consultant.recruiter.employee_name}
CTB : 
{supervisors}
Location: {project.city}
Client :  {project.submission.client}
Role :  {project.submission.lead.job_title}
Start Date :   {str(project.start_date)}\n\n
`Offer count of {project.submission.employer} for this month - {team_offer_count} `
`Total offer count of this month - {total_offer}`
"""
                }
                post_msg_using_webhook(config.offer_url, data)
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

            poc = ConsultantPOC.objects.filter(
                consultant=OuterRef("consultant_id"), end=None, poc_type='recruiter')

            data = projects.annotate(
                client=F('submission__client'),
                status=F('statuses__status'),
                location=F('submission__lead__city'),
                job_title=F('submission__lead__job_title'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_email=F('submission__created_by__email'),
                marketer_name=F('submission__created_by__employee_name'),
                recruiter=Subquery(poc.values('poc__employee_name')[:1]),
            ).values(
                'id', 'client', 'consultant__name', 'consultant__email', 'status', 'feedback', 'client', 'start_date',
                'consultant__phone_no', 'created', 'modified', 'recruiter', 'marketer_name', 'marketer_email', 'vendor',
                'location', 'end_date')

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
            projects = Project.objects.filter(consultant_id=kwargs.get('pk', None), statuses__status='joined')
            if projects:
                project = projects.latest('id')
                if start:
                    queryset = TimeSheet.objects.filter(project=project, start__range=[start, end])
                else:
                    queryset = TimeSheet.objects.filter(project=project)
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
                consultants = Consultant.objects.filter(name__icontains=consultant_name)
            else:
                consultant_ids = Project.objects.filter(
                    statuses__status__in=project_status, statuses__is_current=True
                ).values_list('consultant', flat=True)
                consultants = Consultant.objects.filter(id__in=list(consultant_ids)).exclude(status='archived')

            if query:
                consultants = consultants.filter(
                    Q(name__istartswith=query) |
                    Q(projects__submission__client__icontains=query) |
                    Q(projects__submission__lead__vendor_company__name__icontains=query)
                )
            total = consultants.count()
            serializer = ConsultantTimeSheetSerializer(consultants[first:last], many=True)
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
