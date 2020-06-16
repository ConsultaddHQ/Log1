import os
import difflib
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from rest_framework.mixins import *
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config
from django.db import transaction
from django.db.models.functions import Lower
from django.db.models import Count, Q, F, Max
from django.shortcuts import get_object_or_404

from log1.settings import MEDIA_URL
from marketing.serializers import *
from attachment.views import presigned_post_url
from consultant.models import ConsultantProfile, Consultant
from utils_app.utils import post_msg_using_webhook
from notification.views import create_notification
from attachment.models import Attachment, create_attachment
from utils_app.utils import get_time_filter, get_time_filter_by_start
from utils_app.calendar import get_interviews, book_calendar, update_calendar, delete_calendar_booking

logger = logging.getLogger(__name__)

dont_have_access = 'You don\'t have access'


class MarketingDashboardViewSet(GenericViewSet, ListModelMixin):
    queryset = Submission.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        filter_for = request.query_params.get("filter_for", "")
        filter_by = request.query_params.get("filter_by", "")
        try:
            projects = Project.objects.all()
            interviews = Interview.objects.all()
            sub = Submission.objects.all()
            if filter_for == 'my':
                roles = request.user.roles
                if 'interviewee' in roles:
                    interviews = interviews.filter(
                        Q(submission__created_by=request.user) |
                        Q(supervisor=request.user)
                    )
                else:
                    interviews = interviews.filter(submission__created_by=request.user)

                sub = sub.filter(created_by=request.user)
                projects = projects.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                sub = sub.filter(created_by__team=request.user.team)
                interviews = interviews.filter(submission__created_by__team=request.user.team)
                projects = projects.filter(submission__created_by__team=request.user.team)

            coming_interviews = interviews.filter(status__in=['scheduled', 'rescheduled'])\
                .annotate(
                client=F('submission__client'),
                job_title=F('submission__lead__job_title'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'start_time', 'consultant_name', 'marketer_name', 'vendor', 'client', 'job_title')

            joining = projects.filter(statuses__status='on_boarded', statuses__is_current=True)\
                .annotate(
                client=F('submission__client'),
                vendor=F('submission__lead__vendor_company__name'),
                consultant_name=F('consultant__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'start_date', 'consultant_name', 'marketer_name', 'vendor', 'client', 'is_remote')

            new_offers = projects.filter(statuses__status__in=['new', 'received', 'on_boarded'],
                                         statuses__is_current=True)\
                .annotate(
                client=F('submission__client'),
                consultant_name=F('consultant__name'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'start_date', 'consultant_name', 'marketer_name', 'vendor', 'client', 'is_remote')

            data = {
                "joining": joining[:5],
                "new_offers": new_offers[:5],
                "interviews": coming_interviews[:5]
            }
            if filter_by == 'last_month':
                last = date.today().replace(day=1) - timedelta(days=1)
                first = last.replace(day=1)

            elif filter_by == 'last_6_month':
                last = date.today().replace(day=1) - timedelta(days=1)
                first = last + timedelta(days=1) + relativedelta(months=-6)
            else:
                # this_month
                first = date.today().replace(day=1)
                last = date.today()

            total = projects.count()
            new = projects.filter(statuses__status='new', statuses__is_current=True)
            joined = projects.filter(statuses__status='joined', statuses__is_current=True)
            received = projects.filter(statuses__status='received', statuses__is_current=True)
            on_boarded = projects.filter(statuses__status='on_boarded', statuses__is_current=True)
            not_joined = projects.filter(statuses__status='on_boarded', statuses__is_current=True,
                                         start_date__lt=date.today())
            cancelled = projects.filter(statuses__status__istartswith='cancelled', statuses__is_current=True)
            terminated = projects.filter(statuses__status__istartswith='terminate', statuses__is_current=True)

            sub = sub.filter(created__range=[first, last])
            projects = projects.filter(created__range=[first, last])
            interviews = interviews.filter(created__range=[first, last])
            on_project = Consultant.objects.filter(status='on_project')
            ba_bench = Consultant.objects.filter(skills__contains='BA', status='on_bench')
            dev_bench = Consultant.objects.filter(status='on_bench').exclude(skills__exact='BA')

            count = {
                'offer': projects.count(),
                'submission': sub.count(),
                'ba_bench': ba_bench.count(),
                'dev_bench': dev_bench.count(),
                'interview': interviews.count(),
                'on_project': on_project.count(),
            }

            offer_count = [
                {'name': 'total', 'count': total},
                {'name': 'new', 'count': new.count()},
                {'name': 'joined', 'count': joined.count()},
                {'name': 'received', 'count': received.count()},
                {'name': 'cancelled', 'count': cancelled.count()},
                {'name': 'terminated', 'count': terminated.count()},
                {'name': 'on_boarded', 'count': on_boarded.count()},
                {'name': 'not_joined', 'count': not_joined.count()},
            ]
            return Response({'result': data, 'count': count, 'offer_count': offer_count}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='performance')
    def marketing_performance(self, request):
        filter_for = request.query_params.get("filter_for", "")
        filter_by = request.query_params.get("filter_by", "")
        try:

            if filter_by == 'last_month':
                last = date.today().replace(day=1) - timedelta(days=1)
                first = last.replace(day=1)

            elif filter_by == 'last_6_month':
                last = date.today().replace(day=1) - timedelta(days=1)
                first = last + timedelta(days=1) + relativedelta(months=-6)
            else:
                # this_month
                first = date.today().replace(day=1)
                last = date.today()

            projects = Project.objects.all()

            if filter_for == 'my':
                new_po = projects.filter(statuses__status='joined', created__range=[first, last],
                                         submission__created_by=request.user).count()

                offers_count = projects.filter(submission__created__range=[first, last],
                                               submission__created_by=request.user).count()

                submissions_count = Submission.objects.filter(created__range=[first, last],
                                                              created_by=request.user).count()

                interviews_count = Interview.objects.filter(submission__created__range=[first, last], round='1',
                                                            submission__created_by=request.user).count()

                joining_count = projects.filter(statuses__status='joined', submission__created__range=[first, last],
                                                submission__created_by=request.user).count()

            elif filter_for == 'team':
                new_po = projects.filter(statuses__status='joined', created__range=[first, last],
                                         submission__created_by__team=request.user.team).count()

                offers_count = projects.filter(submission__created__range=[first, last],
                                               submission__created_by__team=request.user.team).count()

                submissions_count = Submission.objects.filter(created__range=[first, last],
                                                              created_by__team=request.user.team).count()

                interviews_count = Interview.objects.filter(submission__created__range=[first, last], round='1',
                                                            submission__created_by__team=request.user.team).count()

                joining_count = projects.filter(statuses__status='joined', submission__created__range=[first, last],
                                                submission__created_by__team=request.user.team).count()

            else:
                new_po = projects.filter(statuses__status='joined', created__range=[first, last]).count()
                offers_count = projects.filter(submission__created__range=[first, last]).count()
                submissions_count = Submission.objects.filter(created__range=[first, last]).count()
                interviews_count = Interview.objects.filter(submission__created__range=[first, last], round='1').count()
                joining_count = projects.filter(statuses__status='joined',
                                                submission__created__range=[first, last]).count()
            prev_po = 0
            if filter_by == 'last_month':
                first = first + relativedelta(months=-1)
                last = last + relativedelta(months=-1)
                prev_po = projects.filter(statuses__status='joined', created__range=[first, last]).count()

            elif filter_by == 'last_6_month':
                first = first + relativedelta(months=-6)
                last = last + relativedelta(months=-6)
                prev_po = projects.filter(statuses__status='joined', created__range=[first, last]).count()

            if prev_po != 0:
                percent = int(((new_po - prev_po) / prev_po) * 100)
            else:
                percent = None

            conversions = {
                "interview": "",
                "joining": "",
                "offers": "",
                "count": {
                    "offer_count": offers_count,
                    "joining_count": joining_count,
                    "interview_count": interviews_count,
                    "submission_count": submissions_count,
                }
            }
            if submissions_count != 0:
                conversions['interview'] = round((interviews_count / submissions_count) * 100, 2)
                conversions['joining'] = round((joining_count / submissions_count) * 100, 2)
                conversions['offers'] = round((offers_count / submissions_count) * 100, 2)

            result = {
                "joined_count": new_po,
                "joined_percent": percent,
                "conversions": conversions
            }
            return Response({"result": result}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='history')
    def dashboard_history(self, request):
        filter_for = request.query_params.get("filter_for", "")
        filter_by = request.query_params.get("filter_by", "")
        try:
            if filter_for == 'my':
                projects = Project.objects.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                projects = Project.objects.filter(submission__created_by__team=request.user.team)
            else:
                projects = Project.objects.all()

            result = []
            if filter_by == 'last_12_month':
                last = date.today().replace(day=1) + relativedelta(months=-11) - timedelta(days=1)
                first = last.replace(day=1)
                for i in range(12):
                    data = {
                        "month": "",
                        "po": ""
                    }
                    projects_count = projects.filter(created__range=[first, last]).count()
                    data["month"] = first.strftime('%b')
                    data["po"] = projects_count
                    result.append(data)
                    first = first + relativedelta(months=1)
                    last = last + relativedelta(months=1)

            elif filter_by == 'last_6_month':
                last = date.today().replace(day=1) + relativedelta(months=-5) - timedelta(days=1)
                first = last.replace(day=1)
                for i in range(6):
                    data = {
                        "month": "",
                        "po": ""
                    }
                    projects_count = projects.filter(created__range=[first, last]).count()
                    data["month"] = first.strftime('%b')
                    data["po"] = projects_count
                    result.append(data)
                    first = first + relativedelta(months=1)
                    last = last + relativedelta(months=1)
            return Response({"result": result}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)


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
                queryset = queryset.filter(status=filter_by_status)

            data_counts = {
                "new": new,
                "sub": sub,
                "draft": draft,
                "total": total,
                "archive": archive,
            }

            if filter_by_status == 'archived':
                data = queryset[first:last].annotate(
                    company_name=F('vendor_company__name'),
                    company_id=F('vendor_company__id'),
                ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills', 'company_id',
                         'company_name', 'is_w2', 'status', 'created', 'modified', 'submission_count')
            else:
                data = queryset.exclude(status='archived')[first:last].annotate(
                    company_name=F('vendor_company__name'),
                    company_id=F('vendor_company__id'),
                ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'secondary_skills', 'company_id',
                         'company_name', 'is_w2', 'status', 'created', 'modified', 'submission_count')

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
                              ).values('id', 'job_desc', 'city', 'job_title', 'primary_skill', 'status', 'created', 'is_w2',
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
                                    , 'company_id', 'company_name', 'modified', 'submission_count', 'is_w2')
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

    @action(methods=['get'], detail=False, url_path='archived')
    def archived(self, request):
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size
            leads = Lead.objects.filter(owner=request.user).annotate(submission_count=Count('submission'))
            data, data_counts = self.get_lead_data(leads, 'archived', first, last)
            if data_counts == 'error':
                return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"results": data, "counts": data_counts}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='map')
    def map(self, request):
        try:
            leads = Lead.objects.filter(
                Q(owner=request.user) |
                Q(shared_to=request.user)
            ).values('city'). \
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
            sub, created = Submission.objects.get_or_create(
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
            sub, created = Submission.objects.get_or_create(
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
            data = {
                "total": sub,
                "sub": sub.filter(status='sub'),
                "project": sub.filter(status='project'),
                "interview": sub.filter(status='interview'),
            }

            if filter_by_status:
                sub = data[filter_by_status]

            data_counts = {
                'total': data["total"].count(),
                'sub': data["sub"].count(),
                'project': data["project"].count(),
                'interview': data["interview"].count()
            }
            data = sub.order_by('-modified')[first:last].annotate(
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
            calendar_id = request.query_params.get('calendar', 'false')
            if calendar_id == 'true':
                interview = get_object_or_404(Interview, calendar_id=kwargs.get('pk'))
                sub = interview.submission
            else:
                sub_id = kwargs.get('pk')
                sub = get_object_or_404(Submission, id=sub_id)

            interviews = Interview.objects.filter(submission=sub.id, supervisor=request.user)
            if interviews:
                serializer = SubmissionDetailSerializer(sub)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)

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
            if query:
                query = query.strip()
                sub = Submission.objects.filter(
                    Q(client__icontains=query) |
                    Q(lead__city__icontains=query) |
                    Q(lead__job_title__icontains=query) |
                    Q(lead__vendor_company__name__icontains=query) |
                    Q(created_by__employee_name__istartswith=query) |
                    Q(vendors__vendor_company__name__icontains=query) |
                    Q(consultant_marketing__consultant__name__icontains=query)
                ).exclude(status='draft')
            else:
                sub = Submission.objects.exclude(
                    Q(consultant_marketing__consultant__status='archived') |
                    Q(status='draft')
                )

            # Team submissions for Scrum master and Proxy Scrum Master
            if 'admin' in roles or 'proxy' in roles:
                sub = sub.filter(
                    Q(created_by__team=request.user.team) |
                    Q(consultant_marketing__in_pool=True) |
                    Q(consultant_marketing__teams=request.user.team)
                )

            # Submissions of a marketer and pool consultant submissions (except those are on project)
            elif 'marketer' in roles:
                consultant_ids = list(request.user.marketed.all().values_list('consultant_id'))
                sub = sub.filter(
                    Q(created_by=request.user) |
                    Q(consultant_marketing__in_pool=True) |
                    Q(consultant_marketing__consultant__in=consultant_ids)
                )

            # Submissions of a Recruiters consultants (except those are on project)
            elif 'recruiter' in roles:
                sub = Submission.objects.filter(
                    Q(consultant_marketing__status='open',
                      consultant_marketing__consultant__pocs__poc=request.user,
                      consultant_marketing__consultant__pocs__poc_type='recruiter'
                      )
                )

            if filter_for == 'my':
                sub = sub.filter(created_by=request.user)
            elif filter_for == 'team':
                sub = sub.filter(created_by__team=request.user.team)

            if consultant_id and consultant_id != 'null':
                sub = sub.filter(consultant_marketing__consultant_id=consultant_id)

            # Submission filter by week, month and all
            sub = get_time_filter(sub, filter_by_time).order_by('-modified').distinct('modified')

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

            data = queryset.order_by('-modified')[first:last].annotate(
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
            roles = request.user.roles
            if query:
                query = query.strip()
                queryset = Interview.objects.filter(
                    Q(submission__client__istartswith=query) |
                    Q(submission__lead__vendor_company__name__icontains=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__email__iexact=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )
            else:
                queryset = Interview.objects.exclude(submission__consultant_marketing__status='close')
            if filter_for == 'my':
                if 'interviewee' in roles:
                    queryset = queryset.filter(
                        Q(submission__created_by=request.user) |
                        Q(supervisor=request.user)
                    )
                else:
                    queryset = queryset.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                queryset = queryset.filter(submission__created_by__team=request.user.team)

            # Interview List for Scrum Master and Proxy Scrum Master (team interviews) and marketer

            if 'admin' in roles or 'proxy' in roles:
                queryset = queryset.filter(
                    Q(submission__consultant_marketing__teams=request.user.team,
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

            queryset = get_time_filter_by_start(queryset, filter_by_time).order_by('-modified').distinct('modified')

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
                                {"email": config.BOOKING_ADMIN},
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

                if os.environ.get('ENV', 'local') == 'prod':
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

                # Mattermost message for Interview
                if date.today() == interview.start_time.date() and interview.screening_type == 'interview':
                    text = "#### :spiral_calendar: New Interview Scheduled \n **CTB:{} :: Round:{} :: {} :: {} :: {} " \
                           ":: {} :: {} **".format(
                        interview.supervisor.employee_name, interview.round, interview.get_interview_mode_display(),
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
                # create_notification(user_list, notification_data)
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
                        {interview.get_interview_mode_display()} :: 
                        {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                        {interview.submission.client} :: {interview.consultant.name} :: 
                        {interview.marketer.employee_name}"""

                if status_change == "true" and interview.status not in ['cancelled']:
                    if interview.status == 'next_round':
                        interview_status = "Next Round"
                        interview_status_emoji = ":+1: "
                    elif interview.status == 'offer':
                        interview_status = "Offer"
                        interview_status_emoji = ":v: "
                    else:
                        interview_status = "Failed"
                        interview_status_emoji = ":-1: "
                    text = f"""#### {interview_status_emoji} Interview Feedback \n **CTB:{interview.supervisor.employee_name} :: {interview.round}R :: {interview.get_interview_mode_display()} :: {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: {interview.submission.client} :: {interview.consultant.name} :: {interview.marketer.employee_name} ({interview_status}) ** \n"""
                    text += interview.feedback

                    data = {
                        "response_type": "in_channel",
                        "username": "Log1 Updates",
                        "text": text,
                    }
                    post_msg_using_webhook(config.interview_feedback_url, data)

                if status_change == 'false':
                    if reschedule == 'true':
                        interview.status = 'rescheduled'
                        interview.save()
                        # Message to mattermost for interview timing updating
                        if date.today() == interview.start_time.date() and interview.screening_type == 'interview':
                            text = "#### :stopwatch: Interview Rescheduled \n **CTB: {} :: Round:{} :: {} :: {} :: " \
                                   "{} :: {} :: {}**".format(
                                interview.supervisor.employee_name, interview.round,
                                interview.get_interview_mode_display(),
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
                        {'email': config.BOOKING_ADMIN},
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
                        if os.environ.get('ENV', 'local') == 'prod':
                            event_id = interview.calendar_id
                            if not event_id:
                                cal_res = book_calendar(event)
                                interview.calendar_id = cal_res['id']
                                interview.save()
                            else:
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
                # create_notification(user_list, notification_data)
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
            if os.environ.get('ENV', 'local') == 'prod':
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
            # create_notification(user_list, notification_data)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='update_notes')
    def update_notes(self, request, *args, **kwargs):
        try:
            queryset = Interview.objects.filter(
                Q(id=kwargs.get('pk')) &
                (
                        Q(submission__created_by=request.user) |
                        Q(supervisor=request.user)
                )
            )
            if queryset:
                interview = queryset.first()
                interview.notes = request.data.get('notes')
                interview.save()
                serializer = InterviewCreateSerializer(interview)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"error": "You are not allowed to upload"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put', 'delete'], detail=True, url_path='upload_recording')
    def upload_recording(self, request, *args, **kwargs):
        try:
            if request.method == 'PUT':
                file_name = request.data['file_name']
                object_id = kwargs.get('pk')
                object_name = f'media/attachments/recordings/{object_id}/{file_name}'
                interview = get_object_or_404(Interview, id=object_id)
                response = presigned_post_url(object_name=object_name)
                interview.attachment_link = MEDIA_URL + f'attachments/recordings/{object_id}/{file_name}'
                interview.save()
                return Response({"result": response}, status=status.HTTP_202_ACCEPTED)
            else:
                interview = get_object_or_404(Interview, id=kwargs.get('pk'))
                interview.attachment_link = None
                interview.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='recording')
    def recording(self, request, *args, **kwargs):
        try:
            from attachment.views import get_s3_object
            object_id = kwargs.get('pk')
            interview = get_object_or_404(Interview, id=object_id)
            if interview.attachment_link:
                url = get_s3_object("/".join(interview.attachment_link.split('/')[4:]))
                return Response({"result": url}, status=status.HTTP_200_OK)
            return Response({"error": "Recording not available"}, status=status.HTTP_400_BAD_REQUEST)
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
                    Q(submission__client__contains=sub.client,
                      submission__consultant_marketing__consultant=sub.consultant_marketing.consultant) |
                    Q(submission__lead__vendor_company=sub.vendor,
                      submission__consultant_marketing__consultant=sub.consultant_marketing.consultant) |
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


class TestViewSets(GenericViewSet, CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin):
    queryset = Test.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            submissions = get_object_or_404(Submission, id=request.data.get('submission'), created_by=request.user)
            if not submissions:
                return Response({"error": 'This is not your submission'}, status=status.HTTP_400_BAD_REQUEST)

            # for file in request.FILES.getlist('file'):
            test = Test.objects.create(
                status='new',
                submission=submissions,
                link=request.data.get('link', None),
                skills=request.data.get('skills', []),
                deadline=request.data.get('deadline', None),
                is_offline=request.data.get('is_offline'),
                additional_details=request.data.get('additional_details'),
            )
            # test email
            # document upload
            serializer = TestCreateSerializer(test)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
