import difflib
import logging
from datetime import date, datetime, timedelta

from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin

from django.db import transaction
from django.db.models import Count, Q, F
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from constants import ENGINEERING

from marketing.serializers import *
from constants import announcement_url
from attachment.models import Attachment
from utils_app.views import get_time_filter, discord_webhook
from utils_app.mailing import send_email_attachment_multiple
from utils_app.calendar import get_interviews, book_calendar, update_calendar, delete_calendar_booking

logger = logging.getLogger(__name__)


class VendorCompanyViewSets(ListModelMixin, CreateModelMixin, GenericViewSet):
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

    def create(self, request, *args, **kwargs):
        queryset = VendorCompany.objects.filter(name__iexact=request.data.get('name', None))
        if queryset:
            return Response({"result": "Company already exist"}, status=status.HTTP_201_CREATED)
        company = VendorCompany.objects.create(
            name=request.data.get('name', None),
            created_by=str(request.user.employee_id) + " - " + request.user.employee_name
        )
        serializer = VendorCompanySerializer(company)
        return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)


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
            roles_have_access = {'superadmin', 'admin', 'proxy', 'marketer', 'interviewee'}
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
            roles_have_access = {'superadmin', 'admin', 'proxy', 'marketer'}
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
            data = sub[first:last].annotate(
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
            sub = Submission.objects.exclude(
                Q(consultant_marketing__consultant__status='archived') |
                Q(status='draft')
            )

            # Team submissions for Scrum master and Proxy Scrum Master
            if 'admin' in roles or 'proxy' in roles:
                sub = sub.filter(
                    (Q(lead__marketer__team=request.user.team) |
                     Q(consultant_marketing__consultant__in_pool=True) |
                     Q(consultant_marketing__consultant__teams=request.user.team))
                )

            # Submissions of a marketer and pool consultant submissions (except those are on project)
            elif 'marketer' in roles:
                sub = sub.filter(
                    (Q(lead__marketer=request.user) |
                     Q(consultant_marketing__consultant__marketer=request.user))
                )

            # Submissions of a Recruiters consultants (except those are on project)
            elif 'recruiter' in roles:
                sub = Submission.objects.filter(
                    Q(consultant_marketing__consultant__pocs__poc=request.user,
                      consultant_marketing__consultant__pocs__poc_type='recruiter',
                      consultant_marketing__consultant__status='in_marketing')
                )

            if filter_for == 'my':
                sub = sub.filter(lead__marketer=request.user)
            elif filter_for == 'team':
                sub = sub.filter(lead__marketer__team=request.user.team)

            if consultant_id and consultant_id != 'null':
                sub = sub.filter(consultant_marketing__consultant_id=consultant_id)

            # Search submission by client, vendor and consultant
            if query:
                query = query.strip()
                sub = sub.filter(
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
                status='draft',
                lead_id=data['lead'],
                consultant_marketing_id=data['consultant']
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
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='resume')
    def resume(self, request, *args, **kwargs):
        attachment_id = kwargs.get('pk')
        attachment = get_object_or_404(Attachment, id=attachment_id)
        attachment.attachment_file = request.FILES.get('file')
        attachment.save()
        serializer = AttachmentSerializer(attachment)
        return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)

    # Suggestions for Submission
    @action(methods=['get'], detail=True, url_path='suggestions')
    def suggestions(self, request, *args, **kwargs):
        client_name = request.query_params.get('client_name', None)
        consultant_id = request.query_params.get('consultant', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            lead = get_object_or_404(Lead, id=kwargs.get('pk'))
            if client_name and client_name != 'null':
                queryset = Submission.objects.filter(
                    Q(consultant_marketing__consultant_id=consultant_id) &
                    Q(client__icontains=client_name)
                )
            else:
                queryset = Submission.objects.filter(
                    Q(consultant_marketing__consultant_id=consultant_id) &
                    Q(lead__vendor_company=lead.vendor_company)
                )

            total = queryset.count()
            data = queryset[first:last].annotate(
                city=F('lead__city'),
                job_title=F('lead__job_title'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('lead__marketer__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),

            ).values('id', 'client', 'consultant_name', 'created', 'marketer_name', 'company_name', 'status',
                     'job_title', 'city')

            return Response({"result": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Suggestions for Client Name (Did you mean)
    @action(methods=['get'], detail=False, url_path='client_name_suggestions')
    def client_name_suggestions(self, request):
        try:
            query = request.query_params.get('client', None)
            client_list = Submission.objects.order_by('client').distinct('client').exclude(
                client=None).values_list('client', flat=True)
            result = difflib.get_close_matches(query, client_list, 1)
            return Response({"result": result}, status=status.HTTP_200_OK)
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
            ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'screening_type',
                     'submission_id', 'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                     'project', 'job_title', 'modified')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

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
                                                                  marketer.employee_name),
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

    # Change status of scheduled and rescheduled Interviews to feedback_due
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

    def retrieve(self, request, *args, **kwargs):
        try:
            self.change_to_feedback_due()
            interview = get_object_or_404(Interview, id=kwargs.get('pk'))
            if request.user in [interview.marketer, interview.supervisor] + list(interview.guest.all()):
                serializer = InterviewDetailSerializer(interview)
            else:
                serializer = self.serializer_class(interview)

            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        filter_for = request.query_params.get('filter_for', 'all')
        filter_by_time = request.query_params.get('filter_by_time', None)
        filter_by_status = request.query_params.get('filter_by_status', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            # Change status of past Interview to feedback due
            self.change_to_feedback_due()

            # Search Interview by Client, VendorContact and Consultant
            queryset = Interview.objects.exclude(submission__consultant_marketing__consultant__status='archived')
            if filter_for == 'my':
                queryset = queryset.filter(submission__lead__marketer=request.user)
            elif filter_for == 'team':
                queryset = queryset.filter(submission__lead__marketer__team=request.user.team)

            # Interview List for Scrum Master and Proxy Scrum Master (team interviews) and marketer
            roles = request.user.roles
            if 'admin' in roles or 'proxy' in roles:
                queryset = queryset.filter(
                    Q(submission__consultant_marketing__consultant__teams=request.user.team,
                      submission__consultant_marketing__in_pool=False) |
                    Q(submission__consultant_marketing__in_pool=True)
                )

            elif 'marketer' in roles:
                queryset = queryset.filter(
                    Q(submission__consultant_marketing__in_pool=True) |
                    Q(submission__consultant_marketing__consultant__marketer=request.user) |
                    Q(submission__lead__marketer=request.user)
                )

            elif 'recruiter' in roles:
                queryset = queryset.filter(
                    Q(submission__consultant_marketing__consultant__pocs__poc=request.user,
                      submission__consultant_marketing__consultant__pocs__poc_type='recruiter')
                )

            elif 'retention_manager' in roles:
                queryset = queryset.filter(
                    Q(submission__consultant_marketing__consultant__pocs__poc=request.user,
                      submission__consultant_marketing__consultant__pocs__poc_type='relation')
                )

            if query:
                query = query.strip()
                queryset = queryset.filter(
                    Q(submission__client__icontains=query) |
                    Q(submission__lead__vendor_company__name__icontains=query) |
                    Q(submission__lead__marketer__employee_name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__email__iexact=query) |
                    Q(submission__consultant_marketing__consultant__name__icontains=query)
                )

            queryset = get_time_filter(queryset, filter_by_time).order_by('-modified').distinct('modified')

            data, screen_data = self.get_interview_data(queryset, filter_by_status, first, last)

            if screen_data == 'error':
                return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": screen_data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        submission_id = request.data['submission']
        try:
            # Change status of past Interview to feedback due
            self.change_to_feedback_due()

            submissions = Submission.objects.filter(id=request.data.get('submission'))
            if not submissions:
                return Response({"error": 'This is not your submission'}, status=status.HTTP_400_BAD_REQUEST)

            # calculating Interview round
            prev_interview = Interview.objects.filter(submission_id=submission_id).exclude(
                status='cancelled').order_by('-created')
            round_count = 0
            if prev_interview:
                round_count = prev_interview.first().round

            # Saving Interview
            serializer = InterviewCreateSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                queryset = Interview.objects.filter(id=serializer.data['id'])
                interview = queryset.first()
                interview.round = round_count + 1
                interview.save()

                # Closing Submission for scheduling Interview
                submission = submissions.first()
                submission.is_active = False
                submission.status = 'interview'
                submission.save()

                # Calendar title
                title = "CTB:{} :: {}R :: {} :: {} :: {} :: {} :: {} :: {}".format(
                    interview.supervisor.employee_name, interview.round, interview.get_screening_type_display(),
                    interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST'), interview.submission.client,
                    interview.consultant, interview.marketer, interview.submission.employer
                )

                # Calendar attendees
                supervisor = interview.supervisor.email
                scrum_master = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
                guest = [{"email": user.email} for user in interview.guest.all()]
                attendees = [
                                {'email': request.user.email},
                                {'email': supervisor},
                                {"email": "bbookingg@gmail.com"}
                            ] + guest
                for user in scrum_master:
                    attendees.append({"email": user.email})

                # Calendar booking start and end time
                start = serializer.data["start_time"].replace("Z", "")
                end = serializer.data["end_time"].replace("Z", "")
                event = {
                    "end": end,
                    "start": start,
                    "summary": title,
                    "user": request.user,
                    "attendees": attendees,
                    "lead": interview.submission.lead,
                    "submission": interview.submission,
                    "consultant": interview.consultant,
                    "description": interview.description,
                    "call_details": interview.call_details,
                }

                # Create new Event in Google Calendar
                cal_res = {
                    'id': 'error'
                }
                try:
                    cal_res = book_calendar(event)
                    interview.calendar_id = cal_res['id']
                    interview.save()
                except Exception as error:
                    logger.error("Calendar booking failed")
                    logger.error(error)
                    logger.error(cal_res)
                    return Response({"result": "Calendar event creation failed", "error": str(error)},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Discord message for Interview
                if date.today() == interview.start_time.date() and interview.screening_type == 'interview':
                    text = f'''
                        CTB:{interview.supervisor.employee_name} 
                        :: Round:{interview.round} 
                        :: {interview.get_screening_type_display()} 
                        :: {interview.start_time.strftime('%m/%d/%Y::%I:%M EST')} 
                        :: {interview.consultant} 
                        :: {interview.submission.client} 
                        :: {interview.marketer}
                    '''

                    content = "**Interview scheduled**"
                    discord_webhook(interview.team, content, text, announcement_url)

                data = queryset.annotate(
                    client=F('submission__client'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__lead__marketer__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'screening_type',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name', 'job_title',
                         'submission_id', 'interview_mode')
                return Response({"result": data[0], 'event_id': cal_res['id']}, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            # Change status of past Screening to feedback due
            self.change_to_feedback_due()
            interview_id = kwargs.get('pk')
            reschedule = request.query_params.get('re', 'no')
            status_change = request.query_params.get('status_change', 'true')
            queryset = Interview.objects.filter(id=interview_id, submission__lead__marketer=request.user)
            if not queryset:
                return Response({"error": "Interview not found"}, status=status.HTTP_400_BAD_REQUEST)

            interview = queryset.first()
            serializer = InterviewCreateSerializer(interview, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Setting Submission is_active value
                if interview.status in ['cancelled', 'next_round']:
                    interview.submission.is_active = True
                if interview.status in ['offer']:
                    interview.submission.is_active = False
                interview.submission.save()

                cal_res = {
                    'id': 'error'
                }
                if status_change == 'false':
                    if reschedule.lower() == 'yes':
                        interview.status = 'rescheduled'
                        interview.save()
                        # Message to discord for interview timing updating
                        if date.today() == interview.start_time.date() and interview.interview_mode == 'interview':
                            text = f"""CTB:{interview.supervisor.employee_name} :: Round:{interview.round} :: 
                                   {interview.get_interview_mode_display()} :: 
                                   {interview.start_time.strftime('%m/%d/%Y::%I:%M EST')} :: {interview.consultant} :: 
                                   {interview.submission.client} :: {interview.marketer}"""
                            content = "**Interview Rescheduled**"
                            discord_webhook(interview.team, content, text, announcement_url)

                    ctb = interview.supervisor.email
                    attendees = [
                        {'email': ctb},
                        {'email': request.user.email},
                        {"email": "bbookingg@gmail.com"}
                    ]
                    scrum_masters = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
                    for user in scrum_masters:
                        attendees.append({'email': user.email})

                    guest = [{"email": user.email} for user in interview.guest.all()]
                    if len(guest) > 0:
                        attendees = attendees + guest

                    title = f"""CTB:{interview.supervisor.employee_name} :: {interview.round}R ::
                            {interview.get_screening_type_display} :: 
                            {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                            {interview.submission.client} :: {interview.consultant} :: {interview.marketer}"""

                    sub = interview.submission

                    if interview.status not in ['offer', 'failed', 'next_round']:
                        start = serializer.data["start_time"].replace("Z", "")
                        end = serializer.data["end_time"].replace("Z", "")
                        event = {
                            "end": end,
                            "start": start,
                            "summary": title,
                            "lead": sub.lead,
                            "submission": sub,
                            "user": request.user,
                            "attendees": attendees,
                            "consultant_profile": sub.consultant,
                            "consultant": sub.consultant.consultant,
                            "description": request.data["description"],
                            "call_details": request.data["call_details"]
                        }

                        # Update interview on Google Calendar
                        event_id = interview.calendar_id
                        try:
                            cal_res['id'] = update_calendar(event_id, event)
                        except Exception as error:
                            logger.error(error)
                            logger.error(cal_res)
                            return Response({"result": "Calendar event update failed", "error": str(error)},
                                            status=status.HTTP_400_BAD_REQUEST)

                data = queryset.annotate(
                    client=F('submission__client'),
                    project=F('submission__project'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__lead__marketer__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'job_title', 'submission_id',
                         'project', 'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                         'screening_type', 'interview_mode')

                return Response({"result": data[0], "event_id": cal_res['id']}, status=status.HTTP_202_ACCEPTED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        interview_id = kwargs.get('pk')
        try:
            # Change status of past Screening to feedback due
            self.change_to_feedback_due()

            interview = get_object_or_404(Interview, id=interview_id, submission__lead__marketer=request.user)
            # Delete from google calendar
            try:
                delete_calendar_booking(interview.calendar_id)
            except Exception as error:
                logger.error(error)
                logger.error("Calendar event deletion failed")
                return Response({"result": "Calendar event deletion failed", "error": str(error)},
                                status=status.HTTP_400_BAD_REQUEST)

            interview.status = 'cancelled'
            interview.save()
            if interview.round == 1:
                interview.submission.status = 'sub'
            interview.submission.is_active = True
            interview.submission.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='cal_interviews')
    def calendar_interviews(self, request):
        end = request.query_params.get('end', None)
        start = request.query_params.get('start', None)
        email = request.query_params.get('email', None)
        start_time = datetime.strptime(start, "%Y-%m-%d")
        end_time = datetime.strptime(end, "%Y-%m-%d")
        start_time = start_time.strftime("%Y-%m-%dT")
        end_time = end_time.strftime("%Y-%m-%dT")
        event = {
            "email": email,
            "start": start_time,
            "end": end_time
        }
        # Get interviews from Google Calendar for specific Email ID
        try:
            data, visibility = get_interviews(event)
            return Response({"result": data, "visibility": visibility}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Suggestions for Interview
    @action(methods=['get'], detail=False, url_path='suggestions')
    def interview_suggestions(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        sub_id = request.query_params.get('sub_id')
        ctb = request.query_params.get('ctb', None)
        sub = get_object_or_404(Submission, id=sub_id)
        try:
            if ctb:
                queryset = Interview.objects.filter(
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__client__contains=sub.client) |
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__lead__vendor_company=sub.vendor) |
                    Q(submission__client__contains=sub.client) |
                    Q(submission__client__contains=sub.client, supervisor=ctb)
                )
            else:
                queryset = Interview.objects.filter(
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__client__contains=sub.client) |
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__lead__vendor_company=sub.vendor) |
                    Q(submission__client__contains=sub.client)
                )

            queryset.order_by('id').distinct('id')
            total = queryset.count()
            data = queryset[first:last].annotate(
                client=F('submission__client'),
                supervisor_name=F('supervisor__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__lead__marketer__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),

            ).values('submission', 'supervisor_name', 'round', 'feedback', 'screening_type', 'marketer_name', 'status',
                     'consultant_name', 'start_time', 'end_time', 'company_name', 'client', 'interview_mode')

            return Response({"result": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
