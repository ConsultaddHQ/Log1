import os
import logging
from datetime import datetime, date

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
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin

from consultant.permissions import ConsultantIsAuthenticated
from consultant.authentication import ConsultantTokenAuthentication, get_consultant

from constants import offer_url
from project.serializers import *
from api_key.permissions import HasAPIKey
from marketing.views import discord_webhook
from utils_app.views import get_time_filter
from consultant.models import ConsultantPOC
from marketing.models import Submission, User
from utils_app.mailing import send_email_attachment_multiple, send_email
from constants import ENGINEERING, FINANCE, RECRUITMENT, RELATIONS, SUPERADMIN, LEGAL

logger = logging.getLogger(__name__)


class ProjectViewSets(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def send_offer_received_mail(self, submission, scrum_master, marketer):
        try:
            recruiter = submission.consultant_marketing.consultant.recruiter.email
            to = [RELATIONS, FINANCE, RECRUITMENT, marketer.email,
                  marketer.team.email]
            cc = [recruiter] + SUPERADMIN
            if scrum_master:
                cc.append(scrum_master)

            mail_data = {
                'cc': cc,
                'to': to,
                'bcc': [],
                'subject': 'Offer Received of {} :: {} :: {} :: {} :: {}'.format(
                    submission.consultant_name, submission.client, str(self.start_date), submission.client,
                    submission.vendor
                ),
                'template': '../templates/offer.html',
                'context': {
                    'start': self.start_date,
                    'rate': submission.rate,
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'marketer_name': submission.marketer,
                    'job_title': submission.lead.job_title,
                    'con_rate': submission.consultant.consultant.rate,
                    'vendor_company': submission.lead.vendor_company.name,
                    'consultant_name': submission.consultant.consultant.name,
                    'consultant_email': submission.consultant.consultant.email,
                },
            }
            res = send_email(mail_data, marketer.email)
            return res, "ok"
        except Exception as error:
            logger.error(error)
            return error, "error"

    @staticmethod
    def support_mail(start_date, submission, scrum_master, marketer):
        try:
            path, recordings = [], []
            recruiter = submission.consultant.consultant.recruiter.email
            resume = submission.attachments.filter(attachment_type='resume')

            recordings = [interview.attachment_link for interview in submission.screening.all()
                          if interview.attachment_link is not None]
            recordings = ", ".join(recordings) if len(recordings) != 0 else "NA"

            if resume:
                path.append(resume.first().attachment_file.path)

            cc = [recruiter, marketer.email, marketer.team.email]

            if scrum_master:
                cc.append(scrum_master)

            consultant_name = submission.consultant_name
            mail_data = {
                'to': [ENGINEERING],
                'cc': cc,
                'bcc': [],
                'subject': 'Support Initiation for {} {} {}'.format(
                    consultant_name, submission.client, submission.lead.location
                ),
                'template': '../templates/support.html',
                'context': {
                    'start': start_date,
                    'recordings': recordings,
                    'employer': submission.employer,
                    'client_name': submission.client,
                    'location': submission.lead.location,
                    'marketer_name': submission.marketer,
                    'job_title': submission.lead.job_title,
                    'consultant_name': submission.consultant.consultant.name,
                    'consultant_email': submission.consultant.consultant.email,
                    'jd': submission.lead.job_desc.replace("\n", " ;newline; "),
                    'consultant_phone_no': submission.consultant.consultant.phone_no,
                },
                'attachments': path
            }
            res = send_email_attachment_multiple(mail_data, marketer.email)
            logger.error("Support mail res for {}".format(marketer.email), res)
            return res, "ok"
        except Exception as error:
            logger.error("Support mail exception error for {}".format(marketer.email), error)
            return error, "error"

    @staticmethod
    def po_mail(self, path, scrum_master_email, po_type):
        marketer = self.submission.lead.marketer
        try:
            vendor = self.submission.vendor_contact
            if not vendor:
                return "Vendor is empty", 'error'
            recruiter = self.submission.consultant.consultant.recruiter.email
            to = [RELATIONS, FINANCE, RECRUITMENT, LEGAL, marketer.team.email, marketer.email]
            cc = [recruiter] + SUPERADMIN

            if scrum_master_email:
                cc.append(scrum_master_email)
            consultant_name = self.submission.consultant_name
            mail_data = {
                'to': to,
                'cc': cc,
                'bcc': [],
                'subject': 'On Boarding of {} :: {} :: {} :: {} :: {}'.format(
                    consultant_name, self.submission.employer, str(self.start_date), self.submission.client, self.vendor
                ),
                'template': '../templates/po.html',
                'context': {
                    'type': po_type,
                    'start': self.start_date,
                    'vendor_name': vendor.name,
                    'rate': self.submission.rate,
                    'vendor_email': vendor.email,
                    'vendor_number': vendor.number,
                    'payment_term': self.payment_term,
                    'client_name': self.submission.client,
                    'vendor_address': self.vendor_address,
                    'client_address': self.client_address,
                    'marketer_name': self.submission.marketer,
                    'invoicing_period': self.invoicing_period,
                    'job_title': self.submission.lead.job_title,
                    'reporting_details': self.reporting_details,
                    'employer': self.submission.employer.title(),
                    'vendor_company': self.submission.lead.vendor_company.name,
                    'con_rate': int(self.submission.consultant.consultant.rate),
                    'consultant_name': self.submission.consultant.consultant.name,
                    'consultant_email': self.submission.consultant.consultant.email,
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
        marketer = self.submission.lead.marketer
        try:
            vendor = self.submission.vendor_contact
            recruiter = self.submission.consultant.consultant.recruiter.email
            to = [RELATIONS, FINANCE, RECRUITMENT, LEGAL, marketer.team.email, recruiter]
            cc = [marketer.email] + SUPERADMIN

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
                    'reason': self.get_status_display(),
                    'client_name': self.submission.client,
                    'vendor_address': self.vendor_address,
                    'client_address': self.client_address,
                    'marketer_name': self.submission.marketer,
                    'job_title': self.submission.lead.job_title,
                    'reporting_details': self.reporting_details,
                    'employer': self.submission.employer.title(),
                    'vendor_company': self.submission.lead.vendor_company.name,
                    'consultant_name': self.submission.consultant.consultant.name,
                    'consultant_email': self.submission.consultant.consultant.email,
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

                for i in project.attachment:
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
                projects = Project.objects.filter(submission__lead__marketer=request.user)
            elif filter_for == 'team':
                projects = Project.objects.filter(submission__lead__marketer__team=request.user.team)
            else:
                projects = Project.objects.all()

            if query:
                projects = projects.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__marketer__full_name__istartswith=query) |
                    Q(submission__consultant__consultant__name__istartswith=query)
                )

            if filter_by_time:
                projects = get_time_filter(projects, filter_by_time)

            # count of project by status
            total = projects.count()
            new = projects.filter(status='new').count()
            joined = projects.filter(status='joined').count()
            received = projects.filter(status='received').count()
            on_boarded = projects.filter(status='on_boarded').count()
            not_joined = projects.filter(status='not_joined').count()

            project = projects.order_by('-modified').distinct('modified')

            if filter_by_status:
                project = projects.filter(status=filter_by_status)

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
                sub.status = 'project'
                sub.save()
                sub.consultant_marketing.consultant.status = 'in_offer'
                sub.consultant_marketing.consultant.save()

                scrum_masters = []
                queryset = User.objects.filter(team=request.user.team, role__name=['admin', 'proxy'])
                for user in queryset:
                    scrum_masters.append({"email": user.email})

                marketer = request.user
                support_mail_res, support_mail_error = self.support_mail(sub, scrum_masters, marketer)
                offer_mail_res, offer_mail_error = self.send_offer_received_mail(sub, scrum_masters, marketer)
                if support_mail_error == 'error' or offer_mail_error == 'error':
                    logger.error(support_mail_res)
                    logger.error(offer_mail_res)
                    return Response({"error": "error", "support_mail_error": str(offer_mail_error),
                                     "offer_mail_error": offer_mail_error}, status=status.HTTP_400_BAD_REQUEST)
                return Response(
                    {"result": serializer.data, "support_mail": support_mail_res, "offer_mail": offer_mail_res},
                    status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        project_id = kwargs.get('pk')
        try:
            project = get_object_or_404(Project, id=project_id)
            prev_status = project.status
            new_status = request.data.get('status', None)

            if new_status and prev_status == 'new' and new_status == 'received':
                project.created = timezone.now()
                project.save()

            if new_status and new_status == 'joined':
                project.submission.consultant.consultant.status = 'on_project'
                project.submission.consultant.consultant.save()

            serializer = self.create_serializer_class(project, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                serializer = self.serializer_class(project)
                day_one = datetime.today().replace(day=1, hour=0, minute=0)

                total_offer = Project.objects.filter(
                    Q(created__gte=day_one) &
                    ~Q(status='new')).count()

                team_offer_count = Project.objects.filter(
                    Q(created__gte=day_one, submission__employer__iexact=project.submission.employer) &
                    ~Q(status='new')).count()
                err = None
                if os.getenv('ENV') == 'prod':
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
                    if prev_status not in termination_status and new_status in termination_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_master, 'PO Termination')
                    elif prev_status not in cancellation_status and new_status in cancellation_status:
                        resp, err = self.po_termination_or_cancellation_mail(project, scrum_master, 'PO Cancellation')

                    # Discord message for PO
                    if prev_status == 'new' and project.status == 'received':
                        interviews = project.submission.screening.exclude(status='cancelled')
                        supervisors = "\n".join(
                            [f"**Round {interview.round} - **{interview.ctb.full_name}" for interview in interviews if
                             interview.ctb])
                        text = f"**Employer - **\t {project.submission.employer.title()}" \
                               f"\n**Marketer - **\t{project.marketer}" \
                               f"\n**Supervisors :**\n {supervisors}" \
                               f"\n**Recruiter - **\t{project.submission.consultant.consultant.recruiter.full_name}" \
                               f"\n**Consultant - **\t{project.consultant}" \
                               f"\n**Client - **\t{project.submission.client}" \
                               f"\n**Role - **\t\t{project.submission.lead.job_title}" \
                               f"\n**Location - **\t{project.submission.lead.location}" \
                               f"\n**Start Date - **\t{str(project.start_date)}" \
                               f"\n\nOffer count of {project.submission.employer} for this month - {team_offer_count}" \
                               f"\nTotal offer count of this month - {total_offer}"
                        content = "**Offer**"
                        discord_webhook(project.team, content, text, offer_url)
                return Response({"result": serializer.data, "error": err}, status=status.HTTP_202_ACCEPTED)
            logger.error(serializer.errors)
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class EngineeringProjectsViewSets(viewsets.GenericViewSet, ListModelMixin):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    authentication_classes = (HasAPIKey,)
    permission_classes = ()

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
                location=F('submission__lead__city'),
                job_title=F('submission__lead__job_title'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_email=F('submission__lead__marketer__email'),
                marketer_name=F('submission__lead__marketer__employee_name'),
                recruiter=Subquery(poc.values('poc__employee_name')[:1]),
            ).values(
                'id', 'client', 'consultant__name', 'consultant__email', 'status', 'feedback', 'client', 'start_date',
                'consultant__phone_no', 'created', 'modified', 'recruiter', 'marketer_name', 'marketer_email', 'vendor',
                'location', 'end_date')

            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(str(error))
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)


# API for Mobile App (For Consultants)
class TimeSheetViewSets(GenericViewSet, ListModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=False, url_path='history')
    def history(self, request, *args, **kwargs):
        try:
            consultant = get_consultant(request)
            project = consultant.get_project()
            if project:
                project = project.first()
                queryset = TimeSheet.objects.filter(project=project)
                serializer = self.serializer_class(queryset, many=True)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": "Project Not Found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            project = request.user.get_project()
            if project:
                project = project.first()
                queryset = TimeSheet.objects.filter(project=project, status__in=['draft', 'rejected'])
                serializer = self.serializer_class(queryset, many=True)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": "Project Not Found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            project = request.user.get_project()
            if project:
                project = project.first()
                timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None), project=project)
                timesheet.status = 'submitted'
                timesheet.hours = float(request.data.get('hours'))
                timesheet.additional_hours = float(request.data.get('additional_hours'))

                # Uploading Timesheet Screenshots to S3
                try:
                    admin_user = User.objects.get(employee_id=1000)
                    content_type = ContentType.objects.get(model='timesheet')
                    screenshot = False
                    if request.FILES.get('file1', None):
                        Attachment.objects.create(
                            object_id=timesheet.id,
                            content_type=content_type,
                            attachment_type='timesheet',
                            attachment_file=request.FILES.get('file1'),
                            creator=admin_user
                        )
                        screenshot = True
                    if request.FILES.get('file2', None):
                        Attachment.objects.create(
                            object_id=timesheet.id,
                            content_type=content_type,
                            attachment_type='timesheet',
                            attachment_file=request.FILES.get('file2'),
                            creator=admin_user
                        )
                        screenshot = True
                    if not screenshot:
                        return Response({"error": "Attachment is required"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as error:
                    logger.error(error)
                    return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

                timesheet.save()
                serializer = self.serializer_class(timesheet)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"error": "Project Not Found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None))
            timesheet.status = 'consultant_rejected'
            timesheet.save()
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class FinanceTimeSheetViewSets(RetrieveModelMixin, ListModelMixin, GenericViewSet):
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
            projects = Project.objects.filter(consultant_id=kwargs.get('pk', None))
            if projects:
                project = projects.latest('id')
                if start:
                    queryset = TimeSheet.objects.filter(project=project, created__range=[start, end])
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
        try:
            query = request.query_params.get('query', None)
            consultant_id = request.query_params.get('consultant', None)
            if consultant_id:
                consultants = Consultant.objects.filter(id=consultant_id)
            else:
                consultants = Consultant.objects.exclude(status='archived')
            if query:
                consultants = Consultant.objects.filter(
                    Q()
                ).exclude(status='archived')
            total = consultants.count()
            serializer = ConsultantTimeSheetSerializer(consultants[first:last], many=True)
            return Response({"results": serializer.data, 'total': total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
