import os
import difflib
import logging
from datetime import datetime, date, timedelta

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin

from django.db.models import Count, Q, F
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from discord_webhook import DiscordWebhook, DiscordEmbed

from constants import ENGINEERING

from utils_app.models import City
from marketing.serializers import *
from constants import announcement_url
from attachment.models import Attachment
from utils_app.views import get_time_filter
from utils_app.mailing import send_email_attachment_multiple
from utils_app.calendar import get_inteviews, book_calendar, update_calendar, delete_calendar_booking

logger = logging.getLogger(__name__)


# Webhook function for Discord App
def discord_webhook(username, content, text, url):
    webhook = DiscordWebhook(url=url, username=username,
                             content=content)
    embed = DiscordEmbed(description=text, color=242424)

    webhook.add_embed(embed)
    webhook.execute()


class VendorCompanyViewSets(ListModelMixin, GenericViewSet):
    queryset = VendorCompany.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorCompanySerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get("query", None)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            query = query.strip()
            queryset = VendorCompany.objects.filter(name__icontains=query.strip()).order_by(Lower('name'))
            total = queryset.count()
            data = queryset[first:last].values('id', 'name', 'created_by')
            return Response({"results": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class VendorContactViewSets(ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = VendorContact.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorContactSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            company_id = request.query_params.get('company')
            queryset = VendorContact.objects.filter(company_id=company_id, created_by=request.user)
            data = queryset.values('id', 'name', 'email', 'number', 'company__name', 'created_by')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        data = request.data
        vendor = VendorContact.objects.filter(email=data['email'], created_by=request.user, company_id=data['company'])
        if vendor:
            return Response({"error": "already exists"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            VendorContact.objects.create(
                name=data['name'],
                email=data['email'],
                number=data['number'],
                created_by=request.user,
                company_id=data['company'],
            )
            return Response({"result": "created"}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        vendor = get_object_or_404(VendorContact, id=kwargs.get('pk'), created_by=request.user)
        try:
            serializer = self.serializer_class(vendor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class LeadViewSets(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_lead_data(queryset, filter_by_status, first, last):
        try:
            total = queryset.count()
            new = queryset.filter(status='new').count()
            sub = queryset.filter(status='sub').count()
            draft = queryset.filter(status='draft').count()
            archive = queryset.filter(status='archived').count()

            if filter_by_status:
                if filter_by_status == 'archived':
                    queryset = queryset.filter(status=filter_by_status).exclude(status='archived')
                else:
                    queryset = queryset.filter(status=filter_by_status)

            data_counts = {
                "new": new,
                "sub": sub,
                "draft": draft,
                "total": total,
                "archive": archive,
            }

            data = queryset.exclude(status='archived')[first:last].annotate(
                company_name=F('vendor_company__name'),
                company_id=F('vendor_company__id'),
                project=F('submission__project')
            ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills', 'company_id',
                     'company_name', 'status', 'created', 'modified', 'submission_count', 'project')

            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        filter_by_time = request.query_params.get('filter_by_time', 'all')
        filter_by_status = request.query_params.get('filter_by_status', None)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            if query:
                leads = Lead.objects.filter(
                    Q(marketer=request.user) & (
                            Q(city__icontains=query) |
                            Q(job_title__icontains=query) |
                            Q(vendor_company__name__icontains=query)
                    )
                ).annotate(submission_count=Count('submission'))

            else:
                leads = Lead.objects.filter(marketer=request.user) \
                    .annotate(submission_count=Count('submission')).order_by('-modified')

            leads = get_time_filter(leads, filter_by=filter_by_time)

            data, data_counts = self.get_lead_data(leads, filter_by_status, first, last)

            if data_counts == 'error':
                return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": data_counts}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            roles_have_access = {'superadmin', 'admin', 'marketer'}
            res = set(roles).issubset(roles_have_access)
            if not res:
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
            serializer = LeadCreateSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                queryset = Lead.objects.filter(id=serializer.data["id"])
                lead = queryset.first()
                lead.marketer = request.user
                lead.save()
                data = queryset.annotate(submission_count=Count('submission')) \
                    .annotate(company_name=F('vendor_company__name'),
                              company_id=F('vendor_company__id'),
                              project=F('submission__project')
                              ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills',
                                       'company_id', 'company_name', 'status', 'created', 'modified', 'submission_count'
                                       , 'project')
                return Response({"result": data[0]}, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            roles_have_access = {'superadmin', 'admin', 'marketer'}
            res = set(roles).issubset(roles_have_access)
            if not res:
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
            queryset = Lead.objects.filter(id=kwargs.get('pk'))
            if not queryset:
                return Response({"error": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
            lead = queryset.first()
            serializer = LeadCreateSerializer(lead, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                data = queryset.annotate(submission_count=Count('submission')) \
                    .annotate(company_name=F('vendor_company__name'),
                              company_id=F('vendor_company__id'),
                              project=F('submission__project')
                              ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills',
                                       'company_id', 'company_name', 'status', 'created', 'modified', 'submission_count'
                                       , 'project')
                return Response({"result": data[0]}, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            lead = get_object_or_404(Lead, id=kwargs.get('pk'))
            lead.status = 'archived'
            lead.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='map')
    def map(self, request):
        try:
            leads = Lead.objects.filter(marketer=request.user).values('city'). \
                annotate(total=Count('city')).order_by('city')
            return Response({"results": leads}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='lead_by_city')
    def lead_by_city(self, request):
        try:
            city = request.query_params.get('query', None)
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size

            leads = Lead.objects.annotate(submission_count=Count('submission')).filter(
                Q(marketer=self.request.user, city__iexact=city)).order_by('-modified')

            data, data_counts = self.get_lead_data(leads, '', first, last)

            if data_counts == 'error':
                return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": data_counts}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class SubmissionViewSets(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = SubmissionSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_submission_data(sub, filter_by_status, first, last):
        try:
            total = sub.count()
            submission = sub.filter(status='sub').count()
            project = sub.filter(status='project').count()
            interview = sub.filter(status='interview').count()

            if filter_by_status:
                sub = sub.filter(status=filter_by_status)

            data_counts = {
                'total': total,
                'sub': submission,
                'project': project,
                'interview': interview
            }
            data = sub.select_related('lead', 'consultant_marketing')[first:last].annotate(
                consultant_name=F('consultant_marketing__consultant__name'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('lead__marketer__employee_name'),
                city=F('lead__city')
            ).values('id', 'client', 'employer', 'status', 'created', 'modified', 'rate', 'consultant_name',
                     'company_name', 'marketer_name', 'city', 'project', 'vendor_contact')

            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, "error"

    def retrieve(self, request, *args, **kwargs):
        try:
            sub_id = kwargs.get('pk')
            sub = get_object_or_404(Submission, id=sub_id)
            if sub.lead.marketer == request.user:
                serializer = SubmissionDetailSerializer(sub)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)
            else:
                serializer = self.serializer_class(sub)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        filter_for = request.query_params.get('filter_for', 'all')
        consultant_id = request.query_params.get('consultant', None)
        filter_by_time = request.query_params.get('filter_by_time', 'all')
        filter_by_status = request.query_params.get('filter_by_status', None)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            roles = request.user.roles
            # For Recruiter Admin
            roles_have_access = {'admin', 'recruiter'}
            res = set(roles).issubset(roles_have_access)

            sub = Submission.objects.filter(
                consultant_marketing__consultant__status__in=['in_marketing', 'in_offer']).exclude(status='draft')

            # For Recruiter Admin
            if res:
                sub = sub.select_related('consultant').filter(
                    Q(consultant_marketing__consultant__recruiter=request.user) |
                    Q(consultant_marketing__consultant__recruiter__team=request.user.team)
                )
            # Team submissions for Scrum master
            elif 'admin' in roles:
                sub = sub.select_related('lead', 'consultant').filter(
                    (Q(lead__marketer__team=request.user.team) |
                     Q(consultant_marketing__consultant__in_pool=True) |
                     Q(consultant_marketing__consultant__teams=request.user.team))
                )

            # Submissions of a marketer and pool consultant submissions (except those are on project)
            elif 'marketer' in request.user.roles:
                sub = sub.select_related('lead', 'consultant').filter(
                    (Q(lead__marketer=request.user) |
                     Q(consultant_marketing__consultant__marketer=request.user))
                )

            # Submissions of a Recruiters consultants (except those are on project)
            elif 'recruiter' in request.user.roles:
                sub = Submission.objects.select_related('consultant').filter(
                    consultant_marketing__consultant__recruiter=request.user,
                    consultant_marketing__consultant__status='in_marketing'
                )

            if filter_for:
                if filter_for == 'my':
                    sub = sub.filter(lead__marketer=request.user)
                elif filter_for == 'team':
                    sub = sub.filter(lead__marketer__team=request.user.team)

            if consultant_id and consultant_id != 'null':
                sub = sub.select_related('lead', 'consultant').filter(consultant_marketing__consultant_id=consultant_id)

            # Search submission by client, vendor and consultant
            if query:
                query = query.strip()
                sub = sub.select_related('lead', 'consultant').filter(
                    Q(lead__marketer=request.user) &
                    (Q(client__icontains=query) |
                     Q(lead__job_title__icontains=query) |
                     Q(lead__location__icontains=query) |
                     Q(lead__vendor_company__name__icontains=query) |
                     Q(consultant_marketing__consultant__name__icontains=query) |
                     Q(lead__marketer__full_name__istartswith=query) |
                     Q(vendors__company__name__icontains=query)
                     )
                )

            # Submission filter by week, month and all
            sub = get_time_filter(sub, filter_by_time).order_by('modified').distinct('modified')

            # Submission filter by status
            data, sub_data = self.get_submission_data(sub, filter_by_status, first, last)

            if sub_data == "error":
                return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": sub_data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            sub = Submission.objects.create(
                lead_id=data['lead'],
                consultant_marketing_id=data['consultant'],
                status='draft'
            )

            content_type = ContentType.objects.get(model='submission')
            resume = request.FILES.get('file', None)
            if resume:
                Attachment.objects.create(
                    object_id=sub.id,
                    content_type=content_type,
                    attachment_type='resume',
                    attachment_file=resume,
                    creator=request.user
                )

            data = {
                "id": sub.id,
                "status": "draft",
                "created": sub.created,
                "modified": sub.modified,
                "consultant_name": sub.consultant_name,
                "consultant_id": sub.consultant.consultant.id,
                "attachments": AttachmentSerializer(sub.attachments.all(), many=True).data,
            }
            return Response({"result": data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            queryset = Submission.objects.filter(id=kwargs.get('pk'), lead__marketer=request.user)
            if not queryset:
                return Response({"error": "Submission not found"}, status=status.HTTP_400_BAD_REQUEST)
            submission = queryset.first()
            serializer = SubmissionCreateSerializer(submission, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                submission.lead.status = 'sub'
                submission.lead.save()

                if submission.vendor_contact:
                    submission.is_active = True
                else:
                    submission.is_active = False
                submission.save()

                data = queryset.annotate(
                    consultant_name=F('consultant_marketing__consultant__name'),
                    company_name=F('lead__vendor_company__name'),
                    marketer_name=F('lead__marketer__employee_name'),
                    city=F('lead__city')
                ).values('id', 'client', 'employer', 'status', 'created', 'modified', 'rate', 'company_name',
                         'is_active',
                         'consultant_name', 'marketer_name', 'city', 'project')
                return Response({"result": data[0]}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class VendorLayerView(ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = VendorLayer.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorLayerSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            submission_id = request.query_params.get('submission')
            vendor_layer = VendorLayer.objects.filter(submission_id=submission_id).order_by('level')
            serializer = self.serializer_class(vendor_layer, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            submission_id = request.data.get('submission')
            queryset = VendorLayer.objects.filter(submission=submission_id)
            level = 0
            if queryset:
                level = queryset.latest('created').level

            vendor_layer = VendorLayer.objects.create(
                level=level + 1,
                submission_id=submission_id,
                company_id=request.data.get('company')
            )

            serializer = self.serializer_class(vendor_layer)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            data = request.data.get('data')
            for index in range(len(data)):
                vendor_layer = get_object_or_404(VendorLayer, id=data[index]['id'])
                vendor_layer.level = index + 1
                vendor_layer.save()

            return Response({"result": 'updated'}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            vendor_layer = get_object_or_404(VendorLayer, id=kwargs.get('pk'))
            vendor_layer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class InterviewViewSets(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def send_test_mail(test, scrum_master):
        try:
            to = [ENGINEERING]
            marketer = test.submission.lead.marketer
            resume = test.submission.attachments.filter(attachment_type='resume')
            cc = [marketer.email]
            if scrum_master:
                cc.append(scrum_master)
            attachments = test.attachments.all()
            path = [attachment.attachment_file.path for attachment in attachments]
            if resume:
                path.append(resume.first().attachment_file.path)

            mail_data = {
                'cc': cc,
                'to': to,
                'subject': 'Test for {} :: {} :: {} :: {}'.format(test.submission.consultant_name,
                                                                  test.submission.vendor, test.submission.client,
                                                                  marketer.full_name),
                'template': '../templates/test_mail.html',
                'context': {
                    'employer': test.submission.employer,
                    'client_name': test.submission.client,
                    'marketer_name': test.submission.marketer,
                    'job_desc': test.submission.lead.job_desc,
                    'job_title': test.submission.lead.job_title,
                    'vendor_company': test.submission.lead.vendor_company.name,
                    'consultant_name': test.submission.consultant.consultant.name,
                    'consultant_email': test.submission.consultant.consultant.email,
                    'consultant_phone': test.submission.consultant.consultant.phone_no,
                },
                'attachments': path,
            }
            res = send_email_attachment_multiple(mail_data, marketer.email)
            return res, "ok"
        except Exception as error:
            logger.error(error)
            return error, "error"

    # Change status of past scheduled and rescheduled Interviews to feedback_due
    @staticmethod
    def change_to_feedback_due():
        try:
            now = datetime.now() - timedelta(hours=4)
            previous_interviews = Interview.objects.filter(end_time__lte=now, status__in=['scheduled', 'rescheduled'])
            for interview in previous_interviews:
                interview.status = 'feedback_due'
                interview.save()
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def get_interview_data(queryset, filter_by_status, first, last):
        try:
            # Interview counts by status
            queryset = queryset.order_by('-modified').distinct('modified')
            total = queryset.count()
            offer = queryset.filter(status='offer').count()
            failed = queryset.filter(status='failed').count()
            scheduled = queryset.filter(status='scheduled').count()
            cancelled = queryset.filter(status='cancelled').count()
            rescheduled = queryset.filter(status='rescheduled').count()
            feedback_due = queryset.filter(status='feedback_due').count()

            data_counts = {
                'total': total,
                'offer': offer,
                'failed': failed,
                'scheduled': scheduled,
                'cancelled': cancelled,
                'rescheduled': rescheduled,
                'feedback_due': feedback_due,
            }

            if filter_by_status:
                queryset = queryset.filter(status=filter_by_status)

            data = queryset[first:last].annotate(
                client=F('submission__client'),
                project=F('submission__project'),
                job_title=F('submission__lead__job_title'),
                supervisor_name=F('supervisor__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__lead__marketer__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'type', 'submission_id',
                     'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name', 'project',
                     'job_title', 'modified')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    def retrieve(self, request, *args, **kwargs):
        try:
            self.change_to_feedback_due()
            screening = get_object_or_404(Interview, id=kwargs.get('pk'))
            if request.user in [screening.submission.lead.marketer, screening.ctb] + list(screening.guest.all()):
                serializer = InterviewDetailSerializer(screening)
            else:
                serializer = self.serializer_class(screening)

            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
