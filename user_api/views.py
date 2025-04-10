import json
from django.db.models import Q
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from employee.models import User
from api_key.models import APIKey
from user_api.models import UserAPIKey

from marketing.utils import date_filter
from marketing.models import Submission, Test, Interview, VendorContact
from marketing.serializers import SubmissionSerializer, TestListSerializer, InterviewSerializer

from user_api.serializers import UserApiSerializer, MarketingTriggerSerializer, CustomPagination
from log1.utils import write_exception, get_page_limits


class UserApiKeyViewSet(GenericViewSet, CreateModelMixin, ListModelMixin, DestroyModelMixin):
    queryset = UserAPIKey.objects.all()
    serializer_class = UserApiSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            user_api = UserAPIKey.objects.filter(user=request.user)
            serializer = self.serializer_class(user_api, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            user_id = request.user.id
            user = get_object_or_404(User, id=user_id)
            try:
                UserAPIKey.objects.get(user=user)
                return Response({"message": "Api key already exists"}, status=status.HTTP_400_BAD_REQUEST)
            except UserAPIKey.DoesNotExist:
                api_key_obj, key = APIKey.objects.create_key(name=f"{user.employee_name}")
                UserAPIKey.objects.create(user=self.request.user, api_key=api_key_obj)
                return Response({"message": "Api Key Created", "data": api_key_obj.api_key}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get('pk', None)
            user = get_object_or_404(User, id=user_id)

            user_api_key = get_object_or_404(UserAPIKey, user=user)
            # user_api_key = UserAPIKey.objects.filter(user=user)
            user_api_key.api_key.delete()
            user_api_key.delete()

            return Response({"message": "API key deleted"}, status=status.HTTP_202_ACCEPTED)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class MarketingPublicApiViewSet(GenericViewSet, ListModelMixin):
    queryset = Submission.objects.all()
    serializer_class = MarketingTriggerSerializer

    @staticmethod
    def verify_api_key(auth_header):
        if auth_header and auth_header.startswith("Token "):
            try:
                api_key = auth_header.split("Token ")[1]
                if not APIKey.objects.is_valid(api_key):
                    return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
                return None
            except IndexError:
                return Response({"message": "Invalid Token Format"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def date_filter_params(timestamp, field_str):
        filters = Q()
        if timestamp and isinstance(timestamp, dict):
            lte_date = timestamp.get('lte', None)
            if lte_date:
                lte_date = (
                        datetime.strptime(lte_date, '%Y-%m-%d').date() + timedelta(days=1)
                ).strftime("%Y-%m-%d")
            lte = lte_date
            gte = timestamp.get('gte', None)

            if lte and gte and lte == gte:
                filters &= Q(**{f"{field_str}__date": lte})
            else:
                if lte:
                    filters &= Q(**{f"{field_str}__lte": lte})
                if gte:
                    filters &= Q(**{f"{field_str}__gte": gte})
        return filters

    def _get_submission_by_id(self, submission_id):
        """Fetch a single submission by ID."""
        try:
            submission_obj = Submission.objects.get(id=int(submission_id))
            serializer = self.get_serializer(submission_obj)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Submission.DoesNotExist:
            return Response({"message": "Submission ID does not exist"}, status=status.HTTP_400_BAD_REQUEST)

    def _apply_filters(self, filters, queryset_filters, queryset_exclude):
        """Apply filters to the query."""
        if 'status' in filters:
            queryset_filters &= Q(status__iexact=filters["status"])

        if 'client' in filters:
            if filters['client'] == "not_null":
                queryset_exclude |= Q(client__isnull=True)
            else:
                queryset_filters &= Q(client__in=filters['client'])

        if 'teams' in filters:
            queryset_filters &= Q(marketing_team__name__in=filters['teams'])

        if 'work_type' in filters:
            queryset_filters &= Q(work_type=filters['work_type'])

        if 'rate' in filters and filters.get("rate") == "not_null":
            queryset_exclude |= Q(rate__isnull=True) | Q(rate=0)

        if 'employer' in filters:
            queryset_filters &= Q(employer__iexact=filters['employer'])

        if 'marketer' in filters:
            queryset_filters &= Q(created_by__name__in=filters['marketer'])

        if 'vendor' in filters:
            queryset_filters &= Q(lead__vendor_company__name__in=filters['vendor'])

        if 'consultant' in filters:
            queryset_filters &= Q(consultant_marketing__consultant__name__in=filters['consultant'])

        if 'position' in filters:
            queryset_filters &= Q(lead__position__name__in=filters["position"])

        if 'incomplete' in filters:
            queryset_exclude |= Q(is_complete=filters['incomplete'])

        if 'created' in filters:
            queryset_filters &= self.date_filter_params(filters['created'], "created")

        return queryset_filters, queryset_exclude

    @action(methods=['get'], detail=False, url_path='marketing_data')
    def get_marketing_data(self, request):
        # API key verification
        auth_response = self.verify_api_key(request.headers.get("Api-Key"))
        if auth_response:
            return auth_response

        # Initialize filters
        sort_by = request.GET.get('sort_by', 'created')
        get_by_id = request.GET.get('submission_id', None)
        filter_json = request.GET.get('filter_json', None)
        queryset_filters = Q()
        queryset_exclude = Q(status__in=['draft', 'archive'])

        try:
            # If fetching a single submission by ID
            if get_by_id and get_by_id.isdigit():
                return self._get_submission_by_id(get_by_id)

            # Apply filters if provided
            if filter_json:
                queryset_filters, queryset_exclude = self._apply_filters(json.loads(filter_json.strip()), queryset_filters, queryset_exclude)
            # Query the database with filters
            queryset = (
                Submission.objects.filter(queryset_filters)
                .exclude(queryset_exclude)
                .order_by(f"-{sort_by}")
            )

            # Paginate results
            context = {"project_filters": Q(employer="consultadd")}
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            serializer = self.get_serializer(paginated_queryset, many=True, context=context)

            return paginator.get_paginated_response(serializer.data)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='submission')
    def get_submission(self, request):
        auth_response = self.verify_api_key(request.headers.get("Api-Key"))
        if auth_response:
            return auth_response
        serializer_class = SubmissionSerializer
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filter_json = request.GET.get('filter_json', None)
            export = json.loads(request.GET.get('export', 'false'))
            filter_by_status = request.GET.get('filter_by_status', None)

            # Base filters: Exclude drafts and archived statuses
            q_filters = ~Q(status__in=['draft', 'archive'])
            if filter_by_status:
                q_filters &= Q(status__in=filter_by_status.split(','))

            if filter_json:
                filters = json.loads(filter_json.strip())

                if 'status' in filters and filters["status"]:
                    q_filters &= Q(status__in=filters["status"])

                if 'client' in filters and filters["client"]:
                    q_filters &= Q(client__in=filters['client'])

                if 'teams' in filters and filters["teams"]:
                    q_filters &= Q(marketing_team__name__in=filters['teams'])

                if 'incomplete' in filters:
                    q_filters &= Q(is_complete=not filters['incomplete'])

                if 'marketer' in filters and filters["marketer"]:
                    q_filters &= Q(created_by_id__in=filters['marketer'])

                if 'vendor' in filters and filters["vendor"]:
                    q_filters &= Q(lead__vendor_company__name__in=filters['vendor'])

                if 'consultant' in filters and filters["consultant"]:
                    q_filters &= Q(consultant_marketing__consultant__name__in=filters['consultant'])

                if 'position' in filters and filters["position"]:
                    q_filters &= Q(lead__position_id__in=filters["position"])

                created = filters.get('created', None)
                if created:
                    q_filters &= date_filter(Q(), created, 'created')  # Assuming `date_filter` works with Q objects

            # Apply filters directly in the query
            queryset = Submission.objects.filter(q_filters)[first:last]
            serializer = serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='test')
    def get_test(self, request):
        auth_response = self.verify_api_key(request.headers.get("Api-Key"))
        if auth_response:
            return auth_response
        serializer_class = TestListSerializer
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filter_json = request.GET.get('filter_json', None)
            export = json.loads(request.GET.get('export', 'false'))
            filter_by_status = request.GET.get('filter_by_status', None)

            q_filters = Q()
            if filter_by_status:
                q_filters &= Q(submission__status__in=filter_by_status.split(','))

            if filter_json:
                filters = json.loads(filter_json)

                if 'client' in filters and filters["client"]:
                    q_filters &= Q(submission__client__in=filters['client'])

                if 'platform' in filters and filters["platform"]:
                    q_filters &= (Q(engineer_feedback__answer__in=filters["platform"]) | Q(
                        platform__in=filters['platform']))

                if 'marketer' in filters and filters["marketer"]:
                    q_filters &= Q(submission__created_by_id__in=filters['marketer'])

                if 'vendor' in filters and filters["vendor"]:
                    q_filters &= Q(submission__lead__vendor_company__name__in=filters['vendor'])

                if 'deadline' in filters and filters.get('deadline'):
                    q_filters &= Q(deadline__lte=filters['deadline'])

                if 'consultant' in filters and filters["consultant"]:
                    q_filters &= Q(submission__consultant_marketing__consultant__name__in=filters['consultant'])

                created = filters.get('created', None)
                if created:
                    q_filters &= date_filter(Q(), created, 'created')

            queryset = Test.objects.filter(q_filters)[first:last]
            serializer = serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='interview')
    def get_interview(self, request):
        auth_response = self.verify_api_key(request.headers.get("Api-Key"))
        if auth_response:
            return auth_response
        serializer_class = InterviewSerializer

        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filter_json = request.GET.get('filter_json', None)
            filter_by_region = request.GET.get('by_region', None)

            q_filters = Q()  # Start with an empty filter

            if filter_json:
                filters = json.loads(filter_json)

                if 'coding_interview' in filters:
                    if filters["coding_interview"] == 'yes':
                        q_filters &= ~Q(guest_type='Not Required') & ~Q(status='cancelled')
                    elif filters["coding_interview"] == 'no':
                        q_filters &= Q(guest_type='Not Required') & ~Q(status='cancelled')

                if 'assignment' in filters:
                    if filters["assignment"] == 'assigned':
                        q_filters &= Q(guest_type__icontains='assigned') & ~Q(status='cancelled')
                    elif filters["assignment"] == 'unassigned':
                        q_filters &= ~Q(guest_type__icontains='assigned') & ~Q(status='cancelled')

                if 'status' in filters and filters["status"]:
                    q_filters &= Q(status__in=filters["status"])

                if 'position' in filters and filters["position"]:
                    q_filters &= Q(submission__lead__position_id__in=filters["position"])

                if 'teams' in filters and filters["teams"]:
                    q_filters &= Q(submission__marketing_team__name__in=filters["teams"])

                if 'ctb' in filters and filters["ctb"]:
                    q_filters &= Q(supervisor__employee_id__in=filters["ctb"])

                if 'client' in filters and filters["client"]:
                    q_filters &= Q(submission__client__in=filters["client"])

                if 'screening_type' in filters and filters["screening_type"]:
                    q_filters &= Q(screening_type__in=filters["screening_type"])

                if 'marketer' in filters and filters["marketer"]:
                    q_filters &= Q(submission__created_by_id__in=filters["marketer"])

                if 'vendor' in filters and filters["vendor"]:
                    q_filters &= Q(submission__lead__vendor_company__name__in=filters["vendor"])

                if 'consultant' in filters and filters["consultant"]:
                    q_filters &= Q(submission__consultant_marketing__consultant__name__in=filters["consultant"])

                start_time = filters.get('start_time', None)
                if start_time:
                    q_filters &= date_filter(Q(), start_time, "start_time")

            if filter_by_region == "canada":
                q_filters &= Q(submission__marketing_team__name="Consultadd Canada")
            elif filter_by_region == "usa":
                q_filters &= ~Q(submission__marketing_team__name="Consultadd Canada")

            queryset = Interview.objects.filter(q_filters)[first:last]
            serializer = serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='vendor_contact')
    def get_vendor_contact(self, request):
        auth_response = self.verify_api_key(request.headers.get("Api-Key"))
        if auth_response:
            return auth_response
        try:
            contact = VendorContact.objects.all()
            data = contact.values('id', 'name', 'email', 'number', 'region', 'company__name')
            return Response({"data": data}, status=200)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)
