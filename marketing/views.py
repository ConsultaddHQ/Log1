import difflib
import logging
from datetime import date, datetime, timedelta

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import *

from constance import config
from django.db import transaction
from django.db.models import Count, Q, F, Max
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from marketing.serializers import *
from utils_app.utils import get_time_filter
from consultant.models import ConsultantProfile
from utils_app.utils import post_msg_using_webhook
from notification.views import create_notification
from attachment.models import Attachment, create_attachment
from utils_app.mailing import send_email_attachment_multiple
from utils_app.calendar import get_interviews, book_calendar, update_calendar, delete_calendar_booking

logger = logging.getLogger(__name__)

dont_have_access = 'You don\'t have access'


class VendorCompanyViewSets(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = VendorCompany.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorCompanySerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get("query", "")
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
        if not ('admin' in request.user.roles or 'superadmin' in request.user.roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        queryset = VendorCompany.objects.filter(name__iexact=request.data.get('name', None))
        if queryset:
            return Response({"result": "Company already exist"}, status=status.HTTP_201_CREATED)
        company = VendorCompany.objects.create(
            name=request.data.get('name', None),
            created_by=str(request.user.employee_id) + " - " + request.user.employee_name
        )
        serializer = VendorCompanySerializer(company)
        return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)


class VendorContactViewSets(RetrieveModelMixin, ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = VendorContact.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorContactSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            company_id = kwargs.get('pk')
            queryset = VendorContact.objects.filter(company_id=company_id, created_by=request.user)
            data = queryset.values('id', 'name', 'email', 'number', 'company__name', 'created_by')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
        email = request.data.get('email', None)
        vendor = VendorContact.objects.filter(email=email, created_by=request.user, company_id=data['company'])
        if vendor:
            return Response({"error": "already exists"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            vendor_contact = VendorContact.objects.create(
                email=email,
                name=data['name'],
                number=data['number'],
                created_by=request.user,
                company_id=data['company'],
            )
            data = {
                "id": vendor_contact.id,
                "name": vendor_contact.name,
                "email": vendor_contact.email,
                "number": vendor_contact.number,
                "company__name": vendor_contact.company.name,
                "created_by": vendor_contact.created_by.employee_name,
            }
            return Response({"result": data}, status=status.HTTP_201_CREATED)
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
            ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills', 'company_id',
                     'company_name', 'status', 'created', 'modified', 'submission_count')

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
                    Q(owner=request.user) & (
                            Q(city__icontains=query) |
                            Q(job_title__icontains=query) |
                            Q(vendor_company__name__icontains=query)
                    )
                ).annotate(submission_count=Count('submission'))

            else:
                leads = Lead.objects.filter(
                    Q(owner=request.user) |
                    Q(shared_to=request.user)
                ).annotate(submission_count=Count('submission')).order_by('-modified')

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
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
            serializer = LeadCreateSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                queryset = Lead.objects.filter(id=serializer.data["id"])
                lead = queryset.first()
                lead.owner = request.user
                lead.save()
                data = queryset.annotate(submission_count=Count('submission')) \
                    .annotate(company_name=F('vendor_company__name'),
                              company_id=F('vendor_company__id'),
                              ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'status', 'created',
                                       'secondary_skills', 'company_id', 'company_name', 'modified', 'submission_count')
                return Response({"result": data[0]}, status=status.HTTP_201_CREATED)
            logger.error(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            queryset = Lead.objects.filter(id=kwargs.get('pk'), owner=request.user)
            if not queryset:
                return Response({"error": "object not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                if queryset.first().owner != request.user:
                    return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
            lead = queryset.first()
            serializer = LeadCreateSerializer(lead, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                data = queryset.annotate(
                    submission_count=Count('submission')
                ).annotate(company_name=F('vendor_company__name'),
                           company_id=F('vendor_company__id'),
                           ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills', 'status'
                                    , 'company_id', 'company_name', 'modified', 'submission_count')
                return Response({"result": data[0]}, status=status.HTTP_202_ACCEPTED)
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

    @action(methods=['get'], detail=False, url_path='leads_by_city')
    def leads_by_city(self, request):
        try:
            city = request.query_params.get('query', None)
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size

            leads = Lead.objects.annotate(submission_count=Count('submission')).filter(
                Q(owner=request.user, city__iexact=city) |
                Q(shared_to=request.user, city__iexact=city)
            ).order_by('-modified')

            data, data_counts = self.get_lead_data(leads, '', first, last)

            if data_counts == 'error':
                return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": data_counts}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


def create_submission(request, lead_id):
    try:
        profile = get_object_or_404(ConsultantProfile, id=request.data['profile_id'])
        vendor_contact = request.data.get('vendor_contact', None)
        if vendor_contact:
            sub = Submission.objects.create(
                status='sub',
                lead_id=lead_id,
                created_by=request.user,
                rate=request.data['rate'],
                email=request.data['email'],
                phone=request.data['phone'],
                client=request.data['client'],
                employer=request.data['employer'],
                vendor_contact_id=request.data['vendor_contact'],
                consultant_marketing_id=request.data['marketing_id'],

                other_link=profile.links,
                visa_end=profile.visa_end,
                linkedin=profile.linkedin,
                education=profile.education,
                visa_type=profile.visa_type,
                visa_start=profile.visa_start,
                current_city=profile.current_city,
                date_of_birth=profile.date_of_birth,
            )
        else:
            sub = Submission.objects.create(
                status='sub',
                lead_id=lead_id,
                created_by=request.user,
                rate=request.data['rate'],
                email=request.data['email'],
                phone=request.data['phone'],
                client=request.data['client'],
                employer=request.data['employer'],
                consultant_marketing_id=request.data['marketing_id'],

                other_link=profile.links,
                visa_end=profile.visa_end,
                linkedin=profile.linkedin,
                education=profile.education,
                visa_type=profile.visa_type,
                visa_start=profile.visa_start,
                current_city=profile.current_city,
                date_of_birth=profile.date_of_birth,
            )

        resume = request.FILES.get('file_resume', None)
        resume_data = {
            "file": resume,
            "type": 'resume',
            "object_id": sub.id,
            "model": "submission",
            "creator": request.user,
        }
        if resume:
            create_attachment(resume_data)

        other = request.FILES.get('file_other', None)
        other_file_data = {
            "file": other,
            "type": 'other',
            "object_id": sub.id,
            "model": "submission",
            "creator": request.user,
        }
        if other:
            create_attachment(other_file_data)

        return sub
    except Exception as error:
        logger.error(error)
        return False


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
                city=F('lead__city'),
                marketer_id=F('created_by'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),
            ).values('id', 'client', 'employer', 'status', 'created', 'modified', 'rate', 'city', 'is_active',
                     'company_name', 'marketer_name', 'marketer_id', 'consultant_name', 'project', 'vendor_contact')

            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, "error"

    def retrieve(self, request, *args, **kwargs):
        try:
            sub_id = kwargs.get('pk')
            sub = get_object_or_404(Submission, id=sub_id)
            if sub.created_by == request.user:
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
        consultant_id = request.query_params.get('consultant_id', None)
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
                    (Q(created_by__team=request.user.team) |
                     Q(consultant_marketing__consultant__in_pool=True) |
                     Q(consultant_marketing__consultant__teams=request.user.team))
                )

            # Submissions of a marketer and pool consultant submissions (except those are on project)
            elif 'marketer' in roles:
                sub = sub.filter(
                    Q(created_by=request.user) |
                    Q(consultant_marketing__marketer=request.user)
                )

            # Submissions of a Recruiters consultants (except those are on project)
            elif 'recruiter' in roles:
                sub = Submission.objects.filter(
                    Q(consultant_marketing__consultant__pocs__poc=request.user,
                      consultant_marketing__consultant__pocs__poc_type='recruiter',
                      consultant_marketing__consultant___marketing__status='open')
                )

            if filter_for == 'my':
                sub = sub.filter(created_by=request.user)
            elif filter_for == 'team':
                sub = sub.filter(created_by__team=request.user.team)

            if consultant_id and consultant_id != 'null':
                sub = sub.filter(consultant_marketing__consultant_id=consultant_id)

            # Search submission by client, vendor and consultant
            if query:
                query = query.strip()
                sub = sub.filter(
                    Q(created_by=request.user) &
                    (Q(client__istartswith=query) |
                     Q(lead__city__istartswith=query) |
                     Q(lead__job_title__istartswith=query) |
                     Q(vendors__company__name__istartswith=query) |
                     Q(created_by__employee_name__istartswith=query) |
                     Q(lead__vendor_company__name__istartswith=query) |
                     Q(consultant_marketing__consultant__name__istartswith=query)
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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            roles_have_access = {'superadmin', 'admin', 'proxy', 'marketer', 'interviewee'}
            res = set(roles).issubset(roles_have_access)
            if not res:
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
            lead_id = request.data.get('lead', None)

            if not lead_id:
                lead = Lead.objects.create(
                    owner=request.user,
                    city=request.data['city'],
                    job_desc=request.data['job_desc'],
                    job_title=request.data['job_title'],
                    primary_skill=request.data['primary_skill'],
                    vendor_company_id=request.data['vendor_company'],
                )
                lead_id = lead.id
            else:
                lead = get_object_or_404(Lead, id=lead_id)

            sub = create_submission(request, lead_id)

            data = {
                "id": sub.id,
                "status": sub.status,
                "created": sub.created,
                "modified": sub.modified,
                "consultant_id": sub.consultant.id,
                "consultant_name": sub.consultant.name,
                "attachments": AttachmentSerializer(sub.attachments.all(), many=True).data,
            }
            if sub.vendor_contact and sub.client:
                sub.is_active = True
            else:
                sub.is_active = False
            sub.save()
            if sub:
                lead.status = 'sub'
                lead.save()
                return Response({"result": data}, status=status.HTTP_201_CREATED)
            return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            submission = get_object_or_404(Submission, id=kwargs.get('pk'), created_by=request.user)
            serializer = SubmissionCreateSerializer(submission, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                if submission.vendor_contact and submission.client:
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
    @action(methods=['get'], detail=False, url_path='suggestions')
    def suggestions(self, request, *args, **kwargs):
        client_name = request.query_params.get('client_name', None)
        consultant_id = request.query_params.get('consultant', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            if request.query_params.get('lead_id') == "0":
                vendor_company = get_object_or_404(VendorCompany, id=request.query_params.get('company_id'))
                if client_name:
                    queryset = Submission.objects.filter(
                        Q(consultant_marketing__consultant_id=consultant_id) &
                        (Q(client__icontains=client_name) | Q(lead__vendor_company=vendor_company))
                    )
                else:
                    queryset = Submission.objects.filter(
                        Q(consultant_marketing__consultant_id=consultant_id) &
                        Q(lead__vendor_company=vendor_company)
                    )
            else:
                lead = get_object_or_404(Lead, id=request.query_params.get('lead_id'))
                if client_name and client_name != 'null':
                    queryset = Submission.objects.filter(
                        Q(consultant_marketing__consultant_id=consultant_id) &
                        (Q(client__icontains=client_name) | Q(lead__vendor_company=lead.vendor_company))
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
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),

            ).values('id', 'client', 'consultant_name', 'created', 'marketer_name', 'company_name', 'status',
                     'job_title', 'city')
            return Response({"result": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Suggestions for Client Name (Did you mean)
    @action(methods=['get'], detail=False, url_path='did_you_mean')
    def did_you_mean(self, request):
        try:
            query = request.query_params.get('client', None)
            client_list = Submission.objects.order_by('client').distinct('client').exclude(
                client=None).values_list('client', flat=True)
            result = difflib.get_close_matches(query, client_list, 1)
            return Response({"result": result}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class VendorLayerViewSets(RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = VendorLayer.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorLayerSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            submission_id = kwargs.get('pk', None)
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
                level = queryset.aggregate(Max('level'))['level__max']

            vendor_layer = VendorLayer.objects.create(
                level=level + 1,
                submission_id=submission_id,
                vendor_company_id=request.data.get('company')
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
                marketer_id=F('submission__created_by'),
                job_title=F('submission__lead__job_title'),
                supervisor_name=F('supervisor__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'interview_mode', 'company_name',
                     'submission_id', 'supervisor_name', 'marketer_name', 'marketer_id', 'consultant_name', 'client',
                     'project', 'job_title', 'modified')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

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
                queryset = queryset.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                queryset = queryset.filter(submission__created_by__team=request.user.team)

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
                    Q(submission__consultant_marketing__marketer=request.user) |
                    Q(submission__created_by=request.user)
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
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__job_title__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__email__iexact=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            queryset = get_time_filter(queryset, filter_by_time).order_by('-modified').distinct('modified')

            data, screen_data = self.get_interview_data(queryset, filter_by_status, first, last)

            if screen_data == 'error':
                return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": screen_data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        submission_id = request.data['submission']
        try:
            # Change status of past Interview to feedback due
            self.change_to_feedback_due()

            submissions = Submission.objects.filter(id=request.data.get('submission'), created_by=request.user)
            if not submissions:
                return Response({"error": 'This is not your submission'}, status=status.HTTP_400_BAD_REQUEST)

            # calculating Interview round
            prev_interview = Interview.objects.filter(submission_id=submission_id).exclude(
                status='cancelled')
            round_count = 0
            if prev_interview and prev_interview.first().status not in ['cancelled', 'next_round']:
                return Response({"error": "change status of previous interview"}, status=status.HTTP_400_BAD_REQUEST)

            if prev_interview:
                round_count = prev_interview.aggregate(Max('round'))['round__max']

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
                title = f"CTB:{interview.supervisor.employee_name} " \
                        f":: {interview.round}R " \
                        f":: {interview.get_interview_mode_display()} " \
                        f":: {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} " \
                        f":: {interview.submission.client} " \
                        f":: {interview.consultant.name} " \
                        f":: {interview.marketer.employee_name} " \
                        f":: {interview.submission.employer}"

                # Calendar attendees
                supervisor = interview.supervisor.email
                scrum_master = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
                guest = [{"email": user.email} for user in interview.guest.all()]
                user_list = [user for user in interview.guest.all()]
                attendees = [
                                {'email': supervisor},
                                {'email': request.user.email},
                                {"email": "bbookingg@gmail.com"},
                            ] + guest
                user_list.append(interview.supervisor)

                for user in scrum_master:
                    user_list.append(user)
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

                # try:
                #     cal_res = book_calendar(event)
                #     interview.calendar_id = cal_res['id']
                #     interview.save()
                # except Exception as error:
                #     logger.error("Calendar booking failed")
                #     logger.error(error)
                #     logger.error(cal_res)
                #     return Response({"result": "Calendar event creation failed", "error": str(error)},
                #                     status=status.HTTP_400_BAD_REQUEST)

                # Mattermost message for Interview
                if date.today() == interview.start_time.date() and interview.screening_type == 'interview':
                    text = '#### :spiral_calendar: New Interview Scheduled \n **CTB:{} :: Round:{} :: {} :: {} :: {} ' \
                           ':: {} :: {} **'.format(
                        interview.supervisor.employee_name, interview.round, interview.get_screening_type_display(),
                        interview.start_time.strftime('%m/%d/%Y::%I:%M EST'), interview.consultant.name,
                        interview.submission.client, interview.marketer.employee_name
                    )
                    data = {
                        "response_type": "in_channel",
                        "username": "Log1 Updates",
                        "text": text,
                    }
                    post_msg_using_webhook(config.announcement_url, data)

                data = queryset.annotate(
                    client=F('submission__client'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'screening_type',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name', 'job_title',
                         'submission_id', 'interview_mode')
                # Creating Notification
                notification_data = {
                    'category': 'info',
                    'description': title,
                    'target_id': interview.id,
                    'target_type': 'interview',
                    'sender_user_type': 'user',
                    'sender_id': request.user.id,
                    'recipient_user_type': 'user',
                    'title': 'New Interview Created',
                }
                create_notification(user_list, notification_data)
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
            status_change = request.query_params.get('status_change', 'true')
            reschedule = request.query_params.get('reschedule', None)
            queryset = Interview.objects.filter(id=interview_id, submission__created_by=request.user)
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
                    interview.submission.status = 'in_offer'
                interview.submission.save()
                cal_res = {
                    'id': 'error'
                }
                scrum_masters = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
                user_list = [user for user in interview.guest.all()]
                user_list.append(interview.supervisor)
                for user in scrum_masters:
                    user_list.append(user)
                title = f"""CTB:{interview.supervisor.employee_name} :: {interview.round}R ::
                        {interview.get_screening_type_display()} :: 
                        {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                        {interview.submission.client} :: {interview.consultant.name} :: 
                        {interview.marketer.employee_name}"""

                if status_change == 'false':
                    if reschedule == 'true':
                        interview.status = 'rescheduled'
                        interview.save()

                        # Message to mattermost for interview timing updating
                        if date.today() == interview.start_time.date() and interview.screening_type == 'interview':
                            text = "#### :stopwatch: Interview Rescheduled \n **CTB: {} :: Round:{} :: {} :: {} :: " \
                                   "{} :: {} :: {}**".format(
                                interview.supervisor.employee_name, interview.round,
                                interview.get_screening_type_display(),
                                interview.start_time.strftime('%m/%d/%Y :: %I:%M EST'),
                                interview.submission.consultant.name,
                                interview.submission.client, interview.marketer.employee_name)
                            data = {
                                "response_type": "in_channel",
                                "username": "Log1 Updates",
                                "text": text,
                            }
                            post_msg_using_webhook(config.announcement_url, data)
                    supervisor_email = interview.supervisor.email
                    attendees = [
                        {'email': supervisor_email},
                        {'email': request.user.email},
                        {'email': 'bbookingg@gmail.com'},
                    ]

                    for user in scrum_masters:
                        attendees.append({'email': user.email})
                    guest = [{"email": user.email} for user in interview.guest.all()]
                    if len(guest) > 0:
                        attendees = attendees + guest

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
                            "consultant": sub.consultant,
                            "description": request.data["description"],
                            "call_details": request.data["call_details"]
                        }

                        # Update interview on Google Calendar
                        # event_id = interview.calendar_id
                        # try:
                        #     cal_res['id'] = update_calendar(event_id, event)
                        # except Exception as error:
                        #     logger.error(error)
                        #     logger.error(cal_res)
                        #     return Response({"result": "Calendar event update failed", "error": str(error)},
                        #                     status=status.HTTP_400_BAD_REQUEST)

                data = queryset.annotate(
                    client=F('submission__client'),
                    project=F('submission__project'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'calendar_id', 'status', 'start_time', 'end_time', 'job_title', 'submission_id',
                         'project', 'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                         'screening_type', 'interview_mode')
                notification_data = {
                    'category': 'info',
                    'description': title,
                    'target_id': interview.id,
                    'target_type': 'interview',
                    'sender_user_type': 'user',
                    'title': 'Interview Updated',
                    'sender_id': request.user.id,
                    'recipient_user_type': 'user',
                }
                create_notification(user_list, notification_data)
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

            interview = get_object_or_404(Interview, id=interview_id, submission__created_by=request.user)
            # Delete from google calendar
            try:
                if interview.calendar_id:
                    delete_calendar_booking(interview.calendar_id)
                else:
                    return Response({"result": "calendar id not found"}, status=status.HTTP_404_NOT_FOUND)
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
            scrum_masters = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])
            user_list = [user for user in interview.guest.all()]
            user_list.append(interview.supervisor)
            for user in scrum_masters:
                user_list.append(user)
            title = f"""CTB:{interview.supervisor.employee_name} :: {interview.round}R ::
                                    {interview.get_screening_type_display()} :: 
                                    {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                                    {interview.submission.client} :: {interview.consultant.name} :: 
                                    {interview.marketer.employee_name}"""

            notification_data = {
                'category': 'info',
                'description': title,
                'target_id': interview.id,
                'target_type': 'interview',
                'sender_user_type': 'user',
                'title': 'Interview Cancelled',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
            }
            create_notification(user_list, notification_data)
            return Response(status=status.HTTP_204_NO_CONTENT)
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
                marketer_name=F('submission__created_by__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),

            ).values('submission', 'supervisor_name', 'round', 'feedback', 'screening_type', 'marketer_name', 'status',
                     'consultant_name', 'start_time', 'end_time', 'company_name', 'client', 'interview_mode')

            return Response({"result": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='calendar_interviews')
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
