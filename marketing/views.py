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
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin

from django.db import transaction
from django.db.models import Count, Q, F
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from discord_webhook import DiscordWebhook, DiscordEmbed

from constants import ENGINEERING

from utils_app.models import City
from marketing.serializers import *
from jd_parser.models import JDParser
from constants import announcement_url
from attachment.models import Attachment
from jd_parser.extraction import extraction
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
            VendorContact(
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
                queryset = queryset.filter(status=filter_by_status)

            data_counts = {
                "new": new,
                "sub": sub,
                "draft": draft,
                "total": total,
                "archive": archive,
            }

            data = queryset[first:last].annotate(
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
                            Q(location__icontains=query) |
                            Q(job_title__icontains=query) |
                            Q(vendor_company__name__icontains=query)
                    )
                ).annotate(submission_count=Count('submission'))

            else:
                leads = Lead.objects.filter(marketer=request.user).exclude(status='archived').annotate(
                    submission_count=Count('submission')).order_by('-modified')

            leads = get_time_filter(leads, filter_by=filter_by_time)

            data, data_counts = self.get_lead_data(leads, filter_by_status, first, last)

            if data_counts == 'error':
                return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"results": data, "counts": data_counts}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
