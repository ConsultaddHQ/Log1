import os
import pytz
import json
import difflib
from datetime import date

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.db.models.functions import Lower
from django.db.models import F, Q, Max, Count
from django.contrib.auth.models import ContentType

from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from engineering.utils import assigned_test_points
from marketing.utils import *
from marketing.serializers import *
from utils_app.models import MapMail
from activity.models import Activity
from utils_app.models import ObjectGroup
from activity.views import create_activity
from employee.models import User, Team, Role
from employee.serializers import TeamSerializer
from django.contrib.auth.models import ContentType
from activity.serializers import ActivitySerializer
from utils_app.calendar import GoogleCalendar, Calendar
from utils_app.mailing import send_email_without_template
from attachment.models import Attachment, create_attachment
from utils_app.slack_notification import MessageCard as slack
from consultant.models import Consultant, ConsultantMarketing
from utils_app.thred_mail import send_email_attachment_multiple
from notification.utils import create_notification, push_notification
from utils_app.aws_utils import presigned_post_url, download_s3_object
from utils_app.utils import delete_temp_file, export_to_csv, generate_s3_url, TECHNOLOGIES
from log1.utils import get_page_limits, post_msg_using_webhook, write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG


# Route - /vendor_company/
class VendorCompanyViewSets(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = VendorCompany.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorCompanySerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get("query", "").lstrip().replace(':amp:', '&')
            first, last = get_page_limits(request) if query else (0, 20)
            queryset = VendorCompany.objects.filter(name__icontains=query).order_by(Lower('name'))
            total = queryset.count()
            data = queryset[first:last].values('id', 'name', 'created_by')
            return Response({"data": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        if not ('admin' in request.user.roles or 'superadmin' in request.user.roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)

        try:
            name = request.data.get('name', None)
            if name:
                name = name.strip().replace(':amp:', '&')
                queryset = VendorCompany.objects.filter(name__icontains=name)
                name = name.strip().replace(':amp:', '&').replace(' ', '').lower()
                for v in queryset:
                    vendor = v.name.strip().replace(' ', '').lower()
                    if name == vendor:
                        return Response({"message": "Company already exist"}, status=400)
                    if name + 's' == vendor:
                        return Response({"message": "Company name already exist with s at the end"}, status=400)
                    if name == vendor + 's':
                        return Response({"message": "Company name already exist without s at the end"}, status=400)
                created_by = str(request.user.employee_id) + " - " + request.user.employee_name
                company = VendorCompany.objects.create(name=request.data.get('name', None), created_by=created_by)
                return Response(
                    {"data": VendorCompanySerializer(company).data, "message": "Vendor Company added"}, status=201
                )
            return Response({"message": "Enter company name"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /vendor_contact/
class VendorContactViewSets(RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = VendorContact.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorContactSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            contact = VendorContact.objects.filter(company_id=kwargs.get('pk'), created_by=request.user)
            data = contact.values('id', 'name', 'email', 'number', 'company__name')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            contact = VendorContact.objects.filter(company_id=request.GET.get('company'), created_by=request.user)
            data = contact.values('id', 'name', 'email', 'number', 'company__name')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', None)
        company = request.data.get('company', None)
        if not company:
            return Response({"message": "Select company"}, status=400)

        vendor = VendorContact.objects.filter(email__iexact=email, created_by=request.user, company_id=company)
        if vendor:
            return Response({"message": "Already exists"}, status=400)
        try:
            contact = VendorContact.objects.create(
                email=email,
                company_id=company,
                created_by=request.user,
                name=request.data['name'],
                number=request.data['number'],
            )
            data = {
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "number": contact.number,
            }
            return Response({"data": data, "message": "Vendor Contact created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /lead/
class LeadViewSets(ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_queryset_and_count(queryset, filter_by_status, sort_by):
        try:
            queryset = queryset.order_by('id').distinct('id')
            data_counts = {
                "total": queryset.count(),
                "new": queryset.filter(status='new').count(),
                "sub": queryset.filter(status='sub').count(),
                "draft": queryset.filter(status='draft').count(),
                "archive": queryset.filter(status='archived').count(),
            }

            if 'archived' in filter_by_status:
                queryset = queryset.filter(status__in=filter_by_status)
            elif len(filter_by_status) > 0:
                queryset = queryset.filter(status__in=filter_by_status).exclude(status='archived')

            if sort_by in ['created', 'modified']:
                order_by = f"-{sort_by}"
            else:
                order_by = "-modified"

            queryset = Lead.objects.filter(id__in=queryset.values('id')).order_by(order_by)
            return queryset, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    @staticmethod
    def get_data(queryset, first=None, last=None):
        if first is not None:
            queryset = queryset[first:last]

        return queryset.annotate(
            company_id=F('vendor_company__id'),
            submission_count=Count('submission'),
            company_name=F('vendor_company__name'),
            position_name=F('position__display_name')
        ).values('id', 'job_desc', 'city', 'job_title', 'position_name', 'primary_skill', 'company_id',
                 'company_name', 'is_w2', 'status', 'created', 'modified', 'submission_count', 'position_type')

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_json = request.GET.get('filter_json', None)
        try:
            queryset = Lead.objects.filter(Q(owner=request.user) | Q(shared_to=request.user))

            if query:
                query = query.lstrip().replace(':amp:', '&')
                queryset = queryset.filter(
                    Q(city__istartswith=query) |
                    Q(job_title__istartswith=query) |
                    Q(vendor_company__name__icontains=query)
                )

            filter_by_status = list()
            if filter_json:
                filters = json.loads(filter_json)

                if 'status' in filters and len(filters["status"]) > 0:
                    filter_by_status = filters["status"]

                if 'position' in filters and len(filters["position"]) > 0:
                    queryset = queryset.filter(position_id__in=filters["position"])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    queryset = queryset.filter(vendor_company__name__in=filters["vendor"])

                created = filters.get('created', None)
                queryset = date_filter(queryset, created, 'created')

            queryset, counts = self.get_queryset_and_count(queryset, filter_by_status, sort_by)

            if counts == 'error':
                return Response({"message": ERROR_MSG, "error": str(queryset)}, status=400)

            data = self.get_data(queryset, first, last)

            return Response({"counts": counts, "data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            queryset = Lead.objects.filter(id=kwargs.get('pk'))
            if queryset:
                data = self.get_data(queryset)
                return Response({"data": data[0]}, status=200)
            return Response({"data": dict()}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if 'marketer' not in roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            serializer = LeadCreateSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                queryset = Lead.objects.filter(id=serializer.data["id"])
                lead = queryset.first()
                lead.owner = request.user
                lead.save()
                data = self.get_data(queryset)
                return Response({"data": data[0], "message": "Requirement added"}, status=201)
            else:
                return Response({"message": "Data is invalid", "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            queryset = Lead.objects.filter(id=kwargs.get('pk'), owner=request.user)
            if not queryset:
                return Response({"message": "Requirement not found"}, status=404)
            else:
                lead = queryset.first()
                if lead.owner != request.user:
                    return Response({"message": DONT_HAVE_ACCESS}, status=403)

            serializer = LeadCreateSerializer(lead, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Activity
                fields = []
                lead_fields = {'job_desc': "Job Description", "city": "City", "is_w2": "W2"}
                lead_fields_keys = lead_fields.keys()
                for field in request.data.keys():
                    if field in lead_fields_keys:
                        fields.append(lead_fields[field])
                desc = f"{request.user.employee_name} updated {', '.join(fields)}"

                if len(lead.job_desc) < 20:
                    submissions = lead.submission.all()
                    submissions.update(is_complete=False)
                for submission in lead.submission.all():
                    submission_is_complete(submission)

                    # Activity
                    create_activity(submission.id, 'submission', request.user, desc, 'updated')

                data = self.get_data(queryset)
                return Response({"data": data[0], "message": "Requirement updated"}, status=202)
            return Response({"message": "Data is invalid", "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            lead = get_object_or_404(Lead, id=kwargs.get('pk'))
            lead.status = 'archived'
            lead.save()
            return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, pk):
        try:
            fields, group = [], None
            users = get_authenticated_users(request=request)
            lead = get_object_or_404(Lead, id=pk, owner__in=users)

            if lead.owner in users:
                group = ObjectGroup.objects.filter(name='owner', model='lead', status=lead.status)

            if group:
                fields = group.first().fields.all().values_list('name', flat=True)
            return Response({"data": fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get', 'put'], detail=False, url_path='archived')
    def archived(self, request):
        try:
            if request.method == 'GET':
                first, last = get_page_limits(request)
                sort_by = request.GET.get('sort_by', None)
                queryset = Lead.objects.filter(owner=request.user)
                queryset, counts = self.get_queryset_and_count(queryset, ['archived'], sort_by)
                if counts == 'error':
                    return Response({"message": ERROR_MSG, "error": str(queryset)}, status=400)
                data = self.get_data(queryset, first, last)
                return Response({"data": data, "counts": counts}, status=200)
            else:
                lead_ids = request.data.get("lead_ids", [])
                if len(lead_ids) <= 0:
                    return Response({"message": "Select data to archive"}, status=400)

                leads = Lead.objects.filter(id__in=lead_ids, owner=request.user, status="new")
                if leads:
                    leads.update(status='archived')
                    return Response({"message": "Requirement Archived"}, status=202)
                return Response({"message": "Data not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /v2/submission/
class SubmissionV2ViewSets(GenericViewSet, RetrieveModelMixin):
    queryset = Submission.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = SubmissionSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            permission = {"update": False}
            sub = get_object_or_404(Submission, id=kwargs.get('pk'))
            users = get_authenticated_users(request)

            if (sub.created_by in users) or (
                    request.user.employee_id == 5693 and sub.consultant.email == 'rajeev.r@consuladd.com'):
                permission['update'] = True
                serializer = SubmissionV2DetailSerializer(sub)
                return Response({"data": serializer.data, "permission": permission}, status=200)
            else:
                serializer = SubmissionV2Serializer(sub)
                return Response({"data": serializer.data, "permission": permission}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='tabs')
    def tabs(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            data = {
                "test": submission.test.exists(),
                "project": hasattr(submission, 'project'),
                "interview": submission.screening.exists(),
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, pk):
        try:
            fields, group = [], None
            submission = get_object_or_404(Submission, id=pk)
            user_ids = get_authenticated_users(request=request, get_id=True)
            if submission.created_by.id in user_ids:
                group = ObjectGroup.objects.filter(name='owner', model='submission', status=submission.status)

            if group:
                fields = group.first().fields.all().values_list('name', flat=True)
            return Response({"data": fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='documents')
    def documents(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            supervisors = list(submission.screening.all().values_list('supervisor_id', flat=True))

            attachments = Attachment.objects.none()
            if submission.created_by.id == request.user.id or request.user.id in supervisors:
                attachments = submission.attachments.all()

            if hasattr(submission, 'project'):
                project = submission.project
                attachments = attachments.union(project.attachments.all())

            for test in submission.test.all():
                attachments = attachments.union(test.attachments.all())

            serializer = AttachmentSerializer(attachments, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='profile')
    def profile(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            serializer = SubmissionConProfile(submission.consultant, context={'submission': submission})
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='activities')
    def activities(self, request, pk):
        try:
            activities = Activity.objects.filter(object_id=pk, content_type__model='submission')
            serializer = ActivitySerializer(activities.order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='resume')
    def resume(self, request, pk):
        try:
            user_id = request.user.id
            data, visibility = list(), False
            submission = get_object_or_404(Submission, id=pk)
            supervisors = list(submission.screening.all().values_list('supervisor_id', flat=True))
            if (submission.created_by.id == user_id) or (user_id in supervisors) or ('engineer' in request.user.roles):
                visibility = True
                queryset = submission.attachments.all()
                data = AttachmentSerializer(queryset, many=True).data
            return Response({"data": data, "visibility": visibility, 'status': submission.status}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='employer')
    def employer(self, request):
        try:
            consultadd_emp = Team.objects.get(name='Consultadd')
            if 'superadmin' in request.user.roles or 'Recruitment' == request.user.team.dept:
                employers = Team.objects.filter(
                    Q(dept='Marketing') | Q(name='Consultadd')
                ).order_by('name').values('id', 'name')
            else:
                teams = request.user.associated_to.all()
                employers = [
                    {"id": request.user.team.id, "name": request.user.team.name},
                    {"id": consultadd_emp.id, "name": consultadd_emp.name},
                ]
                for emp in teams:
                    employers.append({"id": emp.id, "name": emp.name})
            return Response({"data": employers}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='interviews')
    def interviews(self, request, pk):
        try:
            change_to_feedback_due()
            submission = get_object_or_404(Submission, id=pk)
            serializer = InterviewV2Serializer(submission.screening.all(), many=True, context={'user': request.user})
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='tests')
    def tests(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            serializer = TestGetSerializer(submission.test.all(), many=True, context={'user': request.user})
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='support')
    def support(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            if hasattr(submission, 'project'):
                queryset = submission.project.support.all().order_by('-created')
                serializer = SubmissionSupportSerializer(queryset, many=True)
                return Response({"data": {"data": serializer.data, "project": submission.project.id}}, status=200)
            else:
                return Response({"message": "Project not found"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='project')
    def project(self, request, pk):
        try:
            submission = get_object_or_404(Submission, id=pk)
            if hasattr(submission, 'project'):
                serializer = ProjectV2Serializer(submission.project, context={'user': request.user})
                return Response({"data": serializer.data}, status=200)
            else:
                return Response({"message": "Project not found"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /submission/
class SubmissionViewSets(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = Submission.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = SubmissionSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_count_and_queryset(queryset, sub_status, sort_by, first, last):
        try:
            queryset = queryset.order_by('id').distinct('id')
            data_counts = {
                'total': queryset.count(),
                'sub': queryset.filter(status='sub').count(),
                'project': queryset.filter(status='project').count(),
                'interview': queryset.filter(status='interview').count(),
            }

            if sub_status:
                queryset = queryset.filter(status__in=sub_status)

            if sort_by in ['created', 'modified']:
                order_by = f"-{sort_by}"
            else:
                order_by = "-created"

            queryset = Submission.objects.filter(id__in=queryset.values('id')).order_by(order_by)
            data = queryset[first:last].annotate(
                city=F('lead__city'),
                marketer_id=F('created_by'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),
            ).values('id', 'client', 'employer', 'status', 'created', 'modified', 'rate', 'city', 'is_active',
                     'company_name', 'marketer_name', 'marketer_id', 'consultant_name', 'project', 'vendor_contact',
                     'is_complete', 'work_type')

            return data, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_for = request.GET.get('filter_for', 'all')
        filter_json = request.GET.get('filter_json', None)
        export = json.loads(request.GET.get('export', 'false'))
        filter_by_status = request.GET.get('filter_by_status', None)

        try:
            team = request.user.team
            roles = request.user.roles
            associated_teams = request.user.associated_to.all()
            queryset = Submission.objects.exclude(status__in=['draft', 'archive'])
            if query:
                query = query.lstrip().replace(':amp:', '&')
                queryset = queryset.filter(
                    Q(client__istartswith=query) |
                    Q(lead__city__istartswith=query) |
                    Q(lead__job_title__istartswith=query) |
                    Q(lead__vendor_company__name__icontains=query) |
                    Q(created_by__employee_name__istartswith=query) |
                    Q(vendors__vendor_company__name__icontains=query) |
                    Q(consultant_marketing__consultant__name__istartswith=query)
                )
            else:
                queryset = queryset.exclude(consultant_marketing__consultant__status='terminated')

            if ('superadmin' not in roles) and ('admin' not in roles):
                # Team submissions for Scrum master and Proxy Scrum Master
                # if 'admin' in roles or 'proxy' in roles:
                #     consultant_ids = list(Consultant.objects.filter(marketing__teams=team).values_list('id', flat=True)) + \
                #                      list(ConsultantMarketing.objects.filter(
                #                          in_pool=True, status='open').values_list('consultant_id'))
                #     queryset = queryset.filter(
                #         Q(created_by__team=team) |
                #         Q(consultant_marketing__teams=team) |
                #         Q(consultant_marketing__consultant__in=consultant_ids) |
                #         Q(consultant_marketing__consultant__pocs__poc=request.user,
                #           consultant_marketing__consultant__pocs__poc_type='recruiter')
                #     )
                #
                # Submissions of a marketer and pool consultant submissions (except those are on project)
                if 'marketer' in roles:
                    consultant_ids = list(request.user.marketed.filter(status='open').values_list('consultant_id')) + \
                                     list(ConsultantMarketing.objects.filter(
                                         in_pool=True, status='open').values_list('consultant_id'))
                    if 'recruiter' in roles or 'retention_manager' in roles:
                        queryset = queryset.filter(
                            Q(created_by=request.user) |
                            Q(consultant_marketing__consultant__in=consultant_ids) |
                            Q(consultant_marketing__status='open',
                              consultant_marketing__consultant__pocs__poc=request.user)
                        )
                    else:
                        queryset = queryset.filter(
                            Q(created_by=request.user) |
                            Q(marketing_team=request.user.team) |
                            Q(marketing_team__in=associated_teams) |
                            Q(consultant_marketing__consultant__in=consultant_ids)
                        )

            if filter_for == 'my':
                queryset = queryset.filter(created_by=request.user)
            elif filter_for == 'team':
                queryset = queryset.filter(Q(created_by__team=team) | Q(marketing_team__in=associated_teams))
            elif filter_for == 'handover':
                users = get_authenticated_users(request)
                users.remove(request.user)
                queryset = queryset.filter(created_by__in=users)

            if filter_json:
                filter_by_status = list()
                filters = json.loads(filter_json.strip())

                if 'status' in filters and len(filters["status"]) > 0:
                    filter_by_status = filters["status"]

                if 'client' in filters and len(filters["client"]) > 0:
                    queryset = queryset.filter(client__in=filters['client'])

                if 'teams' in filters and len(filters["teams"]) > 0:
                    queryset = queryset.filter(marketing_team__name__in=filters['teams'])

                if 'incomplete' in filters:
                    queryset = queryset.exclude(is_complete=filters['incomplete'])

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    queryset = queryset.filter(created_by_id__in=filters['marketer'])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    queryset = queryset.filter(lead__vendor_company__name__in=filters['vendor'])

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    queryset = queryset.filter(
                        consultant_marketing__consultant__name__in=filters['consultant']
                    )

                created = filters.get('created', None)
                queryset = date_filter(queryset, created, 'created')

            if export:
                first, last = 0, len(queryset)
            data, sub_data = self.get_count_and_queryset(queryset, filter_by_status, sort_by, first, last)
            col_name = [
                {"name": "consultant_name", "display_name": "Consultant Name"},
                {"name": "marketer_name", "display_name": "Marketer Name"},
                {"name": "employer", "display_name": "Employer"},
                {"name": "client", "display_name": "Client"},
                {"name": "company_name", "display_name": "Company Name"},
                {"name": "vendor_contact", "display_name": "Vendor Contact"},
                {"name": "city", "display_name": "City"},
                {"name": "created", "display_name": "Submitted On"}
            ]
            url = ""
            if export:
                url = export_to_csv(
                    data, col_name, f"submission_report_{datetime.now().strftime('%d-%B-%Y')}.csv", request
                )

            if sub_data == "error":
                return Response({"message": ERROR_MSG, "error": str(data), "url": ""}, status=400)

            return Response({"counts": sub_data, "data": data, "url": url}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error), "url": ""}, status=400)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if 'marketer' not in roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
            lead_id = request.data.get('lead', None)

            if not lead_id:
                position_id = request.data.get('position', None)
                if not position_id or position_id == 'null':
                    return Response({"message": "Job Position is empty"}, status=400)

                lead = Lead.objects.create(
                    owner=request.user,
                    position_id=position_id,
                    city=request.data['city'],
                    job_desc=request.data['job_desc'],
                    job_title=request.data['job_title'],
                    position_type=request.data['position_type'],
                    vendor_company_id=request.data['vendor_company']
                )
                lead_id = lead.id
            else:
                lead = get_object_or_404(Lead, id=lead_id)

            sub, msg = create_submission(request, lead_id)

            # Activity
            desc = f"{request.user.employee_name} added submission"
            create_activity(sub.id, 'submission', request.user, desc, 'created')

            if msg == "error":
                return Response({"message": "Submission not created", "error": str(sub)}, status=400)
            if sub and sub.vendor_contact and sub.client:
                sub.is_active = True
            else:
                sub.is_active = False
            sub.save()

            lead.status = 'sub'
            lead.save()

            data = {
                "id": sub.id,
                "status": sub.status,
                "created": sub.created,
                "modified": sub.modified,
                "consultant_id": sub.consultant.id,
                "consultant_name": sub.consultant.name,
                "attachments": AttachmentSerializer(sub.attachments.all(), many=True).data,
            }
            return Response({"data": data, "message": "Submission created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            users = get_authenticated_users(request)
            if request.user.employee_id == 5693:
                submission = get_object_or_404(Submission, id=kwargs.get('pk'))
            else:
                submission = get_object_or_404(Submission, id=kwargs.get('pk'), created_by__in=users)
            prev_work_type = submission.work_type
            serializer = SubmissionCreateSerializer(submission, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Activity
                fields = []
                sub_fields = {
                    "client": "Client", "employer": "Employer", "rate": "Rate",
                    "work_type": "Work Type", "email": "Email", "phone": "Phone Number",
                }
                sub_fields_keys = sub_fields.keys()
                for field in request.data.keys():
                    if field in sub_fields_keys:
                        fields.append(sub_fields[field])
                desc = f"{request.user.employee_name} updated {', '.join(fields)}"
                create_activity(submission.id, 'submission', request.user, desc, 'updated')

                if submission.vendor_contact and submission.client:
                    submission.is_active = True
                else:
                    submission.is_active = False

                if not submission_is_complete(submission):
                    submission.is_complete = False

                submission.save()
                project = Project.objects.filter(submission=submission)
                if project and prev_work_type != serializer.data['work_type']:
                    status = project.first().statuses.filter(is_current=True, status='joined')
                    if status:
                        scrum_master = User.objects.filter(
                            team=submission.created_by.team, role__name__in=['admin', 'proxy']
                        )
                        to = [submission.created_by.email, 'finance@consultadd.com']
                        to.extend(scrum_master)
                        cc = ['arun.k@consultadd.com']
                        mail_data = {
                            'subject': "Project Type Updated",
                            'to': to, 'cc': cc, 'bcc': [],
                            'body': f"Hello Team,\n{request.user.employee_name} changed the {submission.consultant.name}"
                                    f"project's project type for to {submission.get_work_type_display()}\n\nThanks\nRegards\nThe Log1 Team"
                        }
                        send_email_without_template(mail_data, request.user.email, request=request)
                return Response({"data": serializer.data, "message": "Submission updated"}, status=202)
            else:
                return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['get'], detail=False, url_path='feedback_due')
    def marketer_feedback_due(self, request):
        try:
            if 'marketer' not in request.user.roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            pending_before = date.today() - timedelta(days=15)
            test_lst = Test.objects.filter(
                status='feedback_due', submission__created_by=request.user, modified__gte="2022-01-01"
            ).exclude(modified__gte=pending_before)
            interview_lst = Interview.objects.filter(
                status='feedback_due', submission__created_by=request.user, modified__gte="2022-01-01"
            ).exclude(modified__gte=pending_before)

            if test_lst or interview_lst:
                return Response({"marketer_feedback_due": True}, status=202)
            return Response({"marketer_feedback_due": False}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="feedback_check")
    def feedback_check(self, request, pk):
        try:
            data = {'test': False, 'interview': False}
            qs = Submission.objects.filter(id=pk)
            if qs:
                submission = qs.first()
                test_qs = submission.test.filter(status='feedback_due')
                interview_qs = submission.screening.filter(status='feedback_due')
                if test_qs:
                    data['test'] = True
                if interview_qs:
                    data['interview'] = True
            else:
                return Response({"message": "Submission not found"}, status=404)
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='resume')
    def resume(self, request, pk):
        try:
            attachment = get_object_or_404(Attachment, id=pk)
            attachment.attachment_file = request.FILES.get('file')
            attachment.save()

            # Activity
            desc = f"{request.user.employee_name} added resume"
            create_activity(attachment.object_id, 'submission', request.user, desc, 'updated')

            serializer = AttachmentSerializer(attachment)
            return Response({"data": serializer.data, "message": "Resume updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Suggestions for Submission
    @action(methods=['get'], detail=False, url_path='suggestions')
    def suggestions(self, request):
        first, last = get_page_limits(request)
        client_name = request.GET.get('client_name', None)
        consultant_id = request.GET.get('consultant', None)

        try:
            queryset = Submission.objects.filter(consultant_marketing__consultant_id=consultant_id)
            if request.GET.get('lead_id') == "0":
                qs = VendorCompany.objects.filter(id=request.GET.get('company_id'))
                if qs:
                    vendor_company = qs.first()
                else:
                    return Response({"message": "Issue in fetching Suggestions"}, status=400)
                if client_name:
                    queryset = queryset.filter(
                        Q(client__istartswith=client_name) | Q(lead__vendor_company=vendor_company)
                    )
                else:
                    queryset = queryset.filter(lead__vendor_company=vendor_company)
            else:
                lead = get_object_or_404(Lead, id=request.GET.get('lead_id'))
                if client_name and client_name != 'null':
                    queryset = queryset.filter(
                        (Q(client__istartswith=client_name) | Q(lead__vendor_company=lead.vendor_company))
                    )
                else:
                    queryset = queryset.filter(lead__vendor_company=lead.vendor_company)

            total = queryset.count()
            data = queryset[first:last].annotate(
                city=F('lead__city'),
                job_title=F('lead__job_title'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),
            ).values('id', 'client', 'consultant_name', 'created', 'marketer_name', 'company_name', 'status',
                     'job_title', 'city')
            return Response({"data": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Suggestions for Client Name (Did you mean)
    @action(methods=['get'], detail=False, url_path='did_you_mean')
    def did_you_mean(self, request):
        try:
            query = request.GET.get('client', None)
            client_list = Submission.objects.order_by('client').distinct('client').exclude(
                client=None).values_list('client', flat=True)
            result = difflib.get_close_matches(query, client_list, 1)
            return Response({"data": result}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='client')
    def clients(self, request):
        try:
            query = request.GET.get('query', None)
            queryset = Submission.objects.filter(
                client__istartswith=query.lstrip().replace(':amp:', '&')
            ).exclude(client=None).order_by('client').distinct('client').values_list('client', flat=True)
            result = []
            for i in queryset[:50]:
                if len(i.strip()) > 0:
                    result.append(i.strip())
            return Response({"data": result[:10]}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='work_type')
    def work_type(self, request):
        try:
            return Response({"data": Submission.WORK_CHOICES}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='similar_submission')
    def submission_check(self, request):
        try:
            filter_by = request.GET.get('filter_by', None)
            if request.GET.get('lead_id') == "0":
                try:
                    obj = get_object_or_404(VendorCompany, id=request.GET.get('company_id'))
                    vendor_company = obj.name
                except VendorCompany.DoesNotExist:
                    vendor_company = ""
            else:
                lead = get_object_or_404(Lead, id=request.GET.get('lead_id'))
                vendor_company = lead.vendor_company.name

            f_vendor = Q(lead__vendor_company__name__icontains=vendor_company)
            f_client = Q(client__icontains=request.GET.get('client'))
            f_consultant = Q(consultant_marketing__consultant__id=request.GET.get('consultant_id'))

            if filter_by == "client":
                queryset = Submission.objects.filter(f_client, f_consultant)
            elif filter_by == "vendor":
                queryset = Submission.objects.filter(f_vendor, f_consultant)
            else:
                queryset = Submission.objects.filter(f_vendor, f_consultant, f_client)

            data = queryset.annotate(
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),
                vendor_company=F('lead__vendor_company__name')
            ).values('consultant_name', 'marketer_name', 'created', 'status', 'vendor_company', 'client', 'id')

            return Response({"data": data, "total": len(data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /vendor_layer/
class VendorLayerViewSets(RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = VendorLayer.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = VendorLayerSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            vendor_layer = VendorLayer.objects.filter(submission_id=kwargs.get('pk')).order_by('level')
            serializer = self.serializer_class(vendor_layer, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            level = 0
            submission_id = request.data.get('submission')
            queryset = VendorLayer.objects.filter(submission=submission_id)
            if queryset:
                level = queryset.aggregate(Max('level'))['level__max']

            vendor_layer = VendorLayer.objects.create(
                level=level + 1,
                submission_id=submission_id,
                vendor_company_id=request.data.get('company')
            )

            # Activity
            desc = f"{request.user.employee_name} added {vendor_layer.vendor_company.name} as Vendor Layer"
            create_activity(submission_id, 'submission', request.user, desc, 'updated')

            serializer = self.serializer_class(vendor_layer)
            return Response({"data": serializer.data, "message": "Vendor layer added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            data = request.data.get('data')
            for index in range(len(data)):
                vendor_layer = get_object_or_404(VendorLayer, id=data[index]['id'])
                vendor_layer.level = index + 1
                vendor_layer.save()
            return Response({"message": "Vendor layer updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            vendor_layer = get_object_or_404(VendorLayer, id=kwargs.get('pk'))
            vendor_name = vendor_layer.vendor_company.name
            submission_id = vendor_layer.submission.id
            vendor_layer.delete()

            # Activity
            desc = f"{request.user.employee_name} removed {vendor_name} from Vendor Layer"
            create_activity(submission_id, 'submission', request.user, desc, 'updated')

            return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /interview/
class InterviewViewSets(ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def rank_interviews(interview, interview_status):
        try:
            ranked_interviews = list()
            submission = interview.submission
            similar_interviews = Interview.objects.filter(
                round=1,
                submission__client=submission.client,
                submission__lead__city=submission.lead.city,
                submission__lead__position=submission.lead.position,
            ).exclude(status='cancelled').exclude(submission=submission)
            if interview_status == 'create':
                ranked_interviews = similar_interviews.filter(submission__rank=0)
                submission.rank = similar_interviews.count() + 1
                submission.save()
            elif interview_status == 'cancel':
                ranked_interviews = similar_interviews.filter(
                    Q(submission__rank=0) | Q(submission__rank__gt=submission.rank)
                )
                submission.rank = 0
                submission.save()

            if len(ranked_interviews) > 0:
                similar_interviews = similar_interviews.order_by('created')
                for index, inter in enumerate(similar_interviews):
                    inter.submission.rank = index + 1
                    inter.submission.save()
            return interview
        except Exception as error:
            write_exception(message=error)
            return error

    @staticmethod
    def get_count_and_queryset(queryset, filter_by_status, sort_by, first, last):
        try:
            # Interview counts by status
            queryset = queryset.order_by('id').distinct('id')
            data_counts = {
                'total': queryset.count(),
                'offer': queryset.filter(status='offer').count(),
                'failed': queryset.filter(status='failed').count(),
                'scheduled': queryset.filter(status='scheduled').count(),
                'cancelled': queryset.filter(status='cancelled').count(),
                'next_round': queryset.filter(status='next_round').count(),
                'rescheduled': queryset.filter(status='rescheduled').count(),
                'feedback_due': queryset.filter(status='feedback_due').count(),
            }

            if filter_by_status:
                queryset = queryset.filter(status__in=filter_by_status)

            if sort_by in ['created', 'modified', 'start_time']:
                order_by = f"-{sort_by}"
            else:
                order_by = "-modified"

            queryset = Interview.objects.filter(id__in=queryset.values('id')).order_by(order_by)
            serializer = InterviewListSerializer(queryset[first:last], many=True)
            return serializer.data, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    @staticmethod
    def filter_interview_data(queryset, filter_dict, request):
        try:
            filter_by_status = None
            query = filter_dict.get('query', None)
            filter_for = filter_dict.get('filter_for', None)
            filter_json = filter_dict.get('filter_json', None)

            team = request.user.team
            user_id = request.user.id
            associated_teams = request.user.associated_to.all()
            if query:
                query = query.lstrip().replace(':amp:', '&')
                if query.isnumeric():
                    queryset = queryset.filter(
                        Q(id=query) |
                        Q(submission__client__istartswith=query) |
                        Q(submission__created_by__employee_name__istartswith=query) |
                        Q(submission__lead__vendor_company__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__email__iexact=query) |
                        Q(submission__consultant_marketing__consultant__name__istartswith=query)
                    )
                else:
                    queryset = queryset.filter(
                        Q(submission__client__istartswith=query) |
                        Q(submission__created_by__employee_name__istartswith=query) |
                        Q(submission__lead__vendor_company__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__email__iexact=query) |
                        Q(submission__consultant_marketing__consultant__name__istartswith=query)
                    )

            if filter_for == 'my':
                queryset = queryset.filter(
                    Q(submission__created_by_id=user_id) | Q(supervisor_id=user_id) | Q(guest__id=user_id)
                )

            elif filter_for == 'team':
                queryset = queryset.filter(Q(submission__marketing_team=team) |
                                           Q(submission__marketing_team__in=associated_teams))

            elif filter_for == 'handover':
                users = get_authenticated_users(request, get_id=True)
                users.remove(request.user.id)
                queryset = queryset.filter(Q(submission__created_by_id__in=users) | Q(supervisor_id__in=users))

            if filter_json:
                filters = json.loads(filter_json)

                if 'assignment' in filters:
                    if filters["assignment"] == 'assigned':
                        queryset = queryset.filter(guest_type='assigned').exclude(status='cancelled')
                    if filters["assignment"] == 'unassigned':
                        queryset = queryset.filter(guest_type='coder').exclude(status='cancelled')

                if 'coding_interview' in filters:
                    if filters["coding_interview"] == 'yes':
                        queryset = queryset.filter(guest_type__in=['coder', 'assigned']).exclude(status='cancelled')
                    elif filters["coding_interview"] == 'no':
                        queryset = queryset.exclude(guest_type__in=['coder', 'assigned']).exclude(status='cancelled')

                if 'status' in filters and len(filters["status"]) > 0:
                    filter_by_status = filters["status"]

                if 'position' in filters and len(filters["position"]) > 0:
                    queryset = queryset.filter(submission__lead__position_id__in=filters["position"])

                if 'ctb' in filters and len(filters["ctb"]) > 0:
                    queryset = queryset.filter(supervisor__employee_id__in=filters["ctb"])

                if 'client' in filters and len(filters["client"]) > 0:
                    queryset = queryset.filter(submission__client__in=filters["client"])

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    queryset = queryset.filter(submission__created_by_id__in=filters["marketer"])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    queryset = queryset.filter(submission__lead__vendor_company__name__in=filters["vendor"])

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    queryset = queryset.filter(
                        submission__consultant_marketing__consultant__name__in=filters["consultant"]
                    )

                start_time = filters.get('start_time', None)
                queryset = date_filter(queryset, start_time, "start_time")

            return queryset, filter_by_status
        except Exception as error:
            write_exception(message=error, request=request)
            return queryset, filter_by_status

    def retrieve(self, request, *args, **kwargs):
        try:
            change_to_feedback_due()
            permission = {"update": False}
            interview = get_object_or_404(Interview, id=kwargs.get('pk'))
            users = get_authenticated_users(request)
            # if request.user in [interview.marketer, interview.supervisor]:
            if (interview.marketer in users) or (interview.supervisor in users):
                permission['update'] = True

            serializer = InterviewDetailSerializer(interview)
            return Response({"data": serializer.data, "permission": permission}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_for = request.GET.get('filter_for', 'all')
        filter_json = request.GET.get('filter_json', None)

        try:
            # Change status of past Interview to feedback due
            change_to_feedback_due()
            queryset = Interview.objects.exclude(submission__status='archive')
            filter_dict = {
                "query": query, "filter_for": filter_for, "filter_json": filter_json
            }
            queryset, filter_by_status = self.filter_interview_data(queryset, filter_dict, request)

            data, screen_data = self.get_count_and_queryset(queryset, filter_by_status, sort_by, first, last)
            if screen_data == 'error':
                return Response({"message": ERROR_MSG, "error": str(data)}, status=400)

            return Response({"counts": screen_data, "data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='export')
    def export(self, request, *args, **kwargs):
        query = request.GET.get('query', None)
        filter_for = request.GET.get('filter_for', 'all')
        filter_json = request.GET.get('filter_json', None)

        try:
            queryset = Interview.objects.all()
            filter_dict = {
                "query": query, "filter_for": filter_for, "filter_json": filter_json
            }
            queryset, filter_by_status = self.filter_interview_data(queryset, filter_dict, request)

            queryset = queryset.order_by('id').distinct('id')
            serializer = InterviewListSerializer(queryset, many=True)
            if serializer.data:
                report = get_interview_report(serializer.data, request)
                return report
            return Response({"message": "No Data to Extract"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @staticmethod
    def get_interview_details(obj):
        iter_count = 0
        start_time = obj.start_time.strftime('%b %d, %Y, %I %p')
        work_auth = obj.consultant.work_auth.filter(is_current=True).first()
        supervisor_remark = Answer.objects.filter(object_id=obj.id, question_id=50)
        interview_answer_qs = Answer.objects.filter(
            object_id=obj.id, question__form_name='interview').order_by('question__position')
        coding_answer_qs = Answer.objects.filter(
            object_id=obj.id, question__form_name='coding').order_by('question__position')
        coder_names = obj.guest.all()
        coders = ''
        n = 0
        for name in coder_names:
            if n == 0:
                coders = name.employee_name
                n += 1
            else:
                coders = coders + ', ' + name.employee_name
        supervisor_feedback, guest_feedback = '', ''
        for answer_obj in interview_answer_qs:
            if iter_count == 0:
                supervisor_feedback = f'(Q){answer_obj.question.title} ---> {answer_obj.answer}'
                iter_count += 1
                continue
            supervisor_feedback += f', (Q){answer_obj.question.title} ---> {answer_obj.answer}'
        iter_count = 0
        for answer_obj in coding_answer_qs:
            if iter_count == 0:
                guest_feedback = f'(Q){answer_obj.question.title} ---> {answer_obj.answer}'
                iter_count += 1
                continue
            guest_feedback += f', (Q){answer_obj.question.title} ---> {answer_obj.answer}'

        details = [
            obj.id, start_time, obj.marketer.employee_name, obj.consultant.name,
            work_auth.get_visa_type_display() if work_auth else '', obj.supervisor.employee_name,
            obj.submission.lead.job_title, obj.submission.client, obj.submission.vendor.name, obj.status,
            obj.feedback, obj.failure_reason, obj.coding_present, coders,
            supervisor_remark.first().answer if supervisor_remark else '', obj.guest_remark, supervisor_feedback,
            guest_feedback
        ]
        return details

    @action(methods=['get'], detail=False, url_path='export_detail')
    def export_detail(self, request, *args, **kwargs):
        query = request.GET.get('query', None)
        filter_for = request.GET.get('filter_for', 'all')
        filter_json = request.GET.get('filter_json', None)

        try:
            queryset = Interview.objects.all()
            filter_dict = {
                "query": query, "filter_for": filter_for, "filter_json": filter_json
            }
            queryset, filter_by_status = self.filter_interview_data(queryset, filter_dict, request)

            queryset = queryset.order_by('id').distinct('id')
            response = HttpResponse('application/text')
            writer = csv.writer(response)
            writer.writerow(
                ['Interview Id', 'Interview Time', 'Marketer Name', 'Consultant Name', 'Work Auth', 'Supervisor',
                 'Job Title', 'Client', 'Vendor', 'Interview Status', 'Interview Feedback', 'Failure Reason',
                 'Coding Present', 'Coders', 'Supervisor Remark', 'Coders Remark', 'Supervisor Feedback',
                 'Coder Feedback']
            )
            response['Content-Disposition'] = "attachment; filename=InterviewFeedbackReport.csv"
            for obj in queryset:
                data = self.get_interview_details(obj)
                writer.writerow(data)
            return response
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            # Change status of past Interview to feedback due
            change_to_feedback_due()

            users = get_authenticated_users(request)
            submission_id = request.data.get('submission', None)
            submissions = Submission.objects.filter(id=submission_id, created_by__in=users)
            if not submissions:
                return Response({"message": 'This is not your submission'}, status=400)

            # calculating Interview round
            round_count = 0
            prev_interview = Interview.objects.filter(submission_id=submission_id).exclude(status='cancelled')
            if prev_interview and prev_interview.first().status != 'next_round':
                return Response({"message": "Update status of previous interview first"}, status=400)

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

                # Activity
                end = interview.end_time.strftime("%Y-%m-%d %H-%M")
                start = interview.start_time.strftime("%Y-%m-%d %H-%M")
                desc = f"Interview round {interview.round} is scheduled for " \
                       f"{start.split(' ')[0]}-{start.split(' ')[1]} to {end.split(' ')[0]}-{end.split(' ')[1]}"
                create_activity(submission_id, 'submission', request.user, desc, 'created')

                # Closing Submission for scheduling Interview
                submission = submissions.first()
                submission.status = 'interview'
                submission.is_active = False
                submission.save()

                # Ranking Interview
                if interview.round == 1:
                    interview = self.rank_interviews(interview, 'create')

                # Calendar attendees and User for sending notification
                title = get_interview_title(interview)
                # interview.submission.created_by.email
                user_list, attendees = get_users_and_attendees(request, interview)
                end_time = datetime.strptime(str(interview.end_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")
                start_time = datetime.strptime(str(interview.start_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")
                event = {
                    "end": end_time, "summary": title, "start": start_time,
                    "submission": submission, "consultant": interview.consultant,
                    "user": request.user, "attendees": attendees, "lead": submission.lead,
                    "description": interview.description, "call_details": interview.call_details,
                }

                # Booking Calendar
                try:
                    # Booking Google calendar
                    calendar = GoogleCalendar()
                    cal_res, msg = calendar.book_calendar(event, interview.submission.created_by.email, request)

                    if msg == 'error':
                        return Response({"message": "Calendar booking failed", "error": cal_res}, status=400)

                    interview.calendar_id = cal_res['id']
                    interview.if_previous_calendar = False
                    booking_res = 'booked'
                    interview.save()
                except Exception as error:
                    return Response({"message": "Calendar booking failed", "error": str(error)}, status=400)

                # Slack message for Interview
                if date.today() == interview.start_time.date():
                    payload = {
                        "title": ":scroll: New Interview Scheduled",
                        "body": title
                    }
                    # data = MessageCard.get_simple_card(payload)
                    # post_msg_using_webhook(config.slack_announcement_url, data)

                # if interview.guest_type in ['coder', 'assistance']:
                    # coder_request_notification(interview, "Coding request", request)

                data = queryset.annotate(
                    rank=F('submission__rank'),
                    client=F('submission__client'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'status', 'start_time', 'end_time', 'screening_type', 'rank', 'submission_id',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name', 'job_title',
                         'interview_mode')

                # Creating Notification
                notification_data = {
                    'recipient_user_type': 'user', 'description': title,
                    'category': 'info', 'title': 'New Interview Created',
                    'target_id': interview.id, 'parent_id': submission.id,
                    'target_type': 'interview', 'parent_type': 'submission',
                    'sender_id': request.user.id, 'sender_user_type': 'user',
                }
                create_notification(user_list, notification_data)
                return Response({
                    "data": data[0], 'booking_response': booking_res, "message": "Interview created"
                }, status=201)
            return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        # Change status of past Screening to feedback due
        change_to_feedback_due()
        try:
            interview_status = request.data.get('status', None)
            status_change = request.GET.get('status_change', 'true')

            if interview_status and len(interview_status) == 0:
                return Response({"message": "Invalid value of status, Please select status"}, status=400)

            if interview_status == 'cancelled':
                return Response({"message": "Interview can't be cancelled."}, status=400)
            users = get_authenticated_users(request)
            queryset = Interview.objects.filter(id=kwargs.get('pk'), submission__created_by__in=users)
            if not queryset:
                return Response({"message": "Interview not found"}, status=400)

            interview = queryset.first()
            prev_status = interview.status
            pre_guest_type = interview.guest_type
            serializer = InterviewCreateSerializer(interview, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                if status_change == 'false' and prev_status == 'cancelled':
                    interview.status = 'scheduled'
                    interview.save()

                # Setting Submission is_active value
                submission = interview.submission
                if interview.status in ['next_round']:
                    submission.is_active = True
                if interview.status in ['offer']:
                    submission.is_active = False
                    submission.status = 'in_offer'
                submission.save()

                booking_res = 'Interview or Status Updated'
                user_list, _ = get_users_and_attendees(request, interview)
                title = get_interview_title(interview)

                desc = f"Round {interview.round} status is updated"

                if interview.status not in ['offer', 'failed', 'next_round']:
                    _, attendees = get_users_and_attendees(request, interview)
                    end_time = datetime.strptime(str(interview.end_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                        "%Y-%m-%dT%H:%M:%S")
                    start_time = datetime.strptime(str(interview.start_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                        "%Y-%m-%dT%H:%M:%S")
                    event = {
                        "user": request.user, "attendees": attendees,
                        "lead": submission.lead, "submission": submission,
                        "start": start_time, "consultant": submission.consultant,
                        "end": end_time, "description": request.data["description"],
                        "summary": title, "call_details": request.data["call_details"],
                    }

                    # Updating calendar Booking
                    calendar_id = interview.calendar_id
                    calendar = GoogleCalendar()

                    if not calendar_id:
                        # res, msg = calendar.book_ms_calendar(event)
                        res, msg = calendar.book_calendar(event, interview.submission.created_by.email, request)
                        if msg == 'error':
                            return Response({"message": "Calendar booking failed", "error": res}, status=400)

                        interview.calendar_id = res['id']
                        interview.if_previous_calendar = False
                        booking_res = 'booked'
                        interview.save()
                    else:
                        calendar_mail_id = interview.submission.created_by.email
                        if interview.if_previous_calendar:
                            calendar_mail_id = "suman.m@consultadd.com"

                        res, msg = calendar.update_calendar(calendar_id, event, calendar_mail_id, request)
                        if msg == 'booked':
                            interview.calendar_id = res['id']
                            booking_res = 'updated'
                            interview.save()
                        if msg == "error":
                            return Response({"message": "Calendar update failed", "error": res}, status=400)

                # if interview.guest_type in ['coder', 'assistance'] and (
                #         pre_guest_type == 'not_required' or pre_guest_type is None):
                #     coder_request_notification(interview, "Coding request", request)

                if pre_guest_type in ['coder', 'assistance', 'assigned'] and interview.guest_type == 'not_required':
                    # coder_request_notification(interview, "Coding not required for this Interview", request)
                    interview.guest.clear()

                # Activity
                create_activity(submission.id, 'submission', request.user, desc, 'updated')

                data = queryset.annotate(
                    client=F('submission__client'),
                    project=F('submission__project'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'status', 'start_time', 'end_time', 'job_title', 'submission_id', 'project',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                         'screening_type', 'interview_mode')
                notification_data = {
                    'category': 'info', 'description': title,
                    'target_id': interview.id, 'parent_id': submission.id,
                    'target_type': 'interview', 'parent_type': 'submission',
                    'sender_user_type': 'user', 'title': 'Interview Updated',
                    'sender_id': request.user.id, 'recipient_user_type': 'user',
                }
                create_notification(user_list, notification_data)
                return Response(
                    {"data": data[0], "booking_response": booking_res, "message": "Interview updated"}, status=202
                )
            return Response({"message": ERROR_MSG, "error": str(serializer.errors)}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        interview_id = kwargs.get('pk')
        try:
            # Change status of past Screening to feedback due
            change_to_feedback_due()
            users = get_authenticated_users(request)
            interview = get_object_or_404(Interview, id=interview_id, submission__created_by__in=users)
            if os.environ.get('ENV', 'local') == 'prod':
                try:
                    if interview.calendar_id:
                        calendar_mail_id = interview.submission.created_by.email
                        if interview.if_previous_calendar:
                            calendar_mail_id = "suman.m@consultadd.com"
                        calendar = GoogleCalendar()
                        calendar.delete_calendar_booking(interview.calendar_id, calendar_mail_id, request)
                except Exception as error:
                    write_exception(f"Booking deletion failed: {error}", request)
                    return Response({"data": "Calendar booking deletion failed", "error": str(error)}, status=400)

            interview.status = 'cancelled'
            interview.save()

            submission = interview.submission
            desc = f"Interview round {interview.round} is cancelled"
            create_activity(submission.id, 'submission', request.user, desc, 'updated')

            if interview.round == 1:
                submission.status = 'sub'
                interview = self.rank_interviews(interview, 'cancel')

            submission.is_active = True
            submission.save()

            title = f"""CTB:{interview.supervisor.employee_name} :: {interview.round}R ::
                                    {interview.get_screening_type_display()} :: 
                                    {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                                    {submission.client} :: {interview.consultant.name} :: 
                                    {interview.marketer.employee_name}"""

            notification_data = {
                'category': 'info', 'description': title,
                'target_id': interview.id, 'parent_id': submission.id,
                'target_type': 'interview', 'parent_type': 'submission',
                'sender_id': request.user.id, 'sender_user_type': 'user',
                'recipient_user_type': 'user', 'title': 'Interview Cancelled',
            }
            user_list, _ = get_users_and_attendees(request, interview)
            create_notification(user_list, notification_data)
            return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['put'], detail=True, url_path='status')
    def status(self, request, *args, **kwargs):
        # Change status of past Screening to feedback due
        change_to_feedback_due()
        try:
            interview_status = request.data.get('status', None)

            if interview_status and len(interview_status) == 0:
                return Response({"message": "Invalid value of status, Please select status"}, status=400)

            if interview_status == 'cancelled':
                return Response({"message": "Interview can't be cancelled"}, status=400)
            users = get_authenticated_users(request)
            queryset = Interview.objects.filter(id=kwargs.get('pk'), submission__created_by__in=users)
            if not queryset:
                return Response({"message": "Interview not found"}, status=404)

            interview = queryset.first()
            prev_status = interview.get_status_display()
            serializer = InterviewCreateSerializer(interview, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Setting Submission is_active value
                submission = interview.submission
                if interview.status in ['next_round']:
                    submission.is_active = True
                if interview.status in ['offer']:
                    submission.is_active = False
                    submission.status = 'in_offer'
                submission.save()

                title = get_interview_title(interview)
                booking_res = 'Interview Status Updated'
                user_list, _ = get_users_and_attendees(request, interview)
                desc = f"Round {interview.round} status is changed from {prev_status} to "
                if interview.status not in ['cancelled']:
                    if interview.status == 'next_round':
                        desc += "Next round"
                    elif interview.status == 'offer':
                        desc = "Offer"
                    else:
                        desc = "Failed"

                    slack_card_json = interview_feedback_card(interview, request)
                    post_msg_using_webhook(config.slack_interview_feedback_url, slack_card_json)

                # Activity
                create_activity(submission.id, 'submission', request.user, desc, 'updated')

                data = queryset.annotate(
                    client=F('submission__client'),
                    project=F('submission__project'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'status', 'start_time', 'end_time', 'job_title', 'submission_id', 'project',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                         'screening_type', 'interview_mode')
                notification_data = {
                    'category': 'info', 'description': title,
                    'target_id': interview.id, 'parent_id': submission.id,
                    'target_type': 'interview', 'parent_type': 'submission',
                    'sender_user_type': 'user', 'title': 'Interview Updated',
                    'sender_id': request.user.id, 'recipient_user_type': 'user',
                }
                create_notification(user_list, notification_data)
                return Response(
                    {"data": data[0], "booking_response": booking_res, "message": "Interview updated"}, status=202
                )
            return Response({"message": ERROR_MSG, "error": str(serializer.errors)}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='reschedule')
    def reschedule(self, request, pk):
        # Change status of past Screening to feedback due
        change_to_feedback_due()
        try:
            users = get_authenticated_users(request)
            queryset = Interview.objects.filter(id=pk, submission__created_by__in=users)
            if not queryset:
                return Response({"message": "This is not your Interview"}, status=404)

            interview = queryset.first()
            prev_guest_type = interview.guest_type
            serializer = InterviewCreateSerializer(interview, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

            interview.status = 'rescheduled'
            if interview.guest_type in ['coder', 'assistance', 'assigned']:
                interview.guest.clear()
            interview.save()

            submission = interview.submission
            user_list, attendees = get_users_and_attendees(request, interview)
            title = get_interview_title(interview)

            # Activity
            end = interview.end_time
            start = interview.start_time
            desc = f"Interview round {interview.round} is rescheduled from {start.date()} :: {start.time()} " \
                   f"to {end.date()} :: {end.time()}"
            create_activity(submission.id, 'submission', request.user, desc, 'updated')

            if interview.status not in ['offer', 'failed', 'next_round']:
                end_time = datetime.strptime(str(interview.end_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")
                start_time = datetime.strptime(str(interview.start_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")
                event = {
                    "lead": submission.lead, "submission": submission, "consultant": submission.consultant,
                    "call_details": request.data["call_details"], "user": request.user, "attendees": attendees,
                    "end": end_time, "description": request.data["description"], "start": start_time, "summary": title,
                }

                # Updating calendar Booking
                calendar_id = interview.calendar_id
                calendar = GoogleCalendar()
                if not calendar_id:
                    try:
                        cal_res, msg = calendar.book_calendar(event, interview.submission.created_by.email, request)
                        if msg == "error":
                            return Response({"message": "Calendar booking failed", "error": cal_res}, status=400)

                        interview.calendar_id = cal_res['id']
                        interview.if_previous_calendar = False
                        booking_res = 'booked'
                        interview.save()
                    except Exception as error:
                        return Response({"message": "Calendar reschedule failed", "error": str(error)}, status=400)
                else:
                    try:
                        calendar_mail_id = interview.submission.created_by.email
                        if interview.if_previous_calendar:
                            calendar_mail_id = "suman.m@consultadd.com"
                        res, msg = calendar.update_calendar(calendar_id, event, calendar_mail_id, request)
                        booking_res = 'updated'
                        if msg == 'booked':
                            interview.calendar_id = res['id']
                            booking_res = 'booked'
                            interview.save()
                        if msg == 'error':
                            return Response({"message": "Calendar reschedule failed", "error": res}, status=400)
                    except Exception as error:
                        return Response({"message": "Calendar reschedule failed", "error": str(error)}, status=400)

                # Activity
                desc = f"Interview round {interview.round} is rescheduled from {start.date()} :: {start.time()} " \
                       f"to {end.date()} :: {end.time()}"
                create_activity(submission.id, 'submission', request.user, desc, 'updated')

                if date.today() <= interview.start_time.date():
                    payload = {
                        "body": title,
                        "title": ":stopwatch: Interview Rescheduled",
                    }
                    # data = MessageCard.get_simple_card(payload)
                    # post_msg_using_webhook(config.slack_announcement_url, data)

                if prev_guest_type in ['coder', 'assistance', 'assigned'] and interview.guest_type == 'not_required':
                    est = pytz.timezone('US/Eastern')
                    today = datetime.now().astimezone(est)

                    if today.date() < interview.start_time.date():
                        title = "Coding request, Interview Rescheduled"
                    #     coder_request_notification(interview, title, request)

                    if today.date() == interview.start_time.date() and today.time() < interview.start_time.time():
                        title = "Coding request, Interview Rescheduled"
                    #     coder_request_notification(interview, title, request)

                    if interview.guest_type in ['coder', 'assistance'] and prev_guest_type == 'not_required':
                        title = "Coding request"
                    #     coder_request_notification(interview, title, request)

                data = queryset.annotate(
                    client=F('submission__client'),
                    project=F('submission__project'),
                    job_title=F('submission__lead__job_title'),
                    supervisor_name=F('supervisor__employee_name'),
                    company_name=F('submission__lead__vendor_company__name'),
                    marketer_name=F('submission__created_by__employee_name'),
                    consultant_name=F('submission__consultant_marketing__consultant__name'),
                ).values('id', 'round', 'status', 'start_time', 'end_time', 'job_title', 'submission_id', 'project',
                         'supervisor_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
                         'screening_type', 'interview_mode')

                notification_data = {
                    'parent_id': submission.id, 'sender_user_type': 'user', 'target_type': 'interview',
                    'parent_type': 'submission', 'title': 'Interview Updated', 'sender_id': request.user.id,
                    'category': 'info', 'description': title, 'target_id': interview.id, 'recipient_user_type': 'user',
                }
                create_notification(user_list, notification_data)
                return Response({"data": data[0], "calendar": booking_res, "message": "Interview updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='cancel_interview')
    def cancel_interview(self, request, pk):
        try:
            users = get_authenticated_users(request)
            interview = Interview.objects.get(id=pk)
            sup_condition = all([
                interview.round > 1,
                interview.supervisor not in users,
                interview.status not in ['scheduled', 'rescheduled'],
                interview.supervisor.employee_id not in [1001, 9999]
            ])
            if sup_condition:
                return Response({"message": "Please ask supervisor to cancel this round"}, status=404)

            marketer_condition = all([
                (interview.status in ['scheduled', 'rescheduled'] or interview.round <= 1),
                interview.marketer not in users
            ])
            if marketer_condition:
                return Response({"message": "You don't have access"}, status=404)

            try:
                if interview.calendar_id:
                    calendar_mail_id = interview.submission.created_by.email
                    if interview.if_previous_calendar:
                        calendar_mail_id = "suman.m@consultadd.com"
                    calendar = GoogleCalendar()
                    calendar.delete_calendar_booking(interview.calendar_id, calendar_mail_id, request)
            except Exception as error:
                write_exception(f"Booking cancellation failed: {error}", request)
                # return Response({"data": "Calendar booking cancellation failed", "error": str(error)}, status=400)

            interview.feedback = request.data.get('feedback', None)
            interview.status = 'cancelled'
            interview.save()

            submission = interview.submission

            # Activity
            desc = f"Interview round {interview.round} is cancelled"
            create_activity(submission.id, 'submission', request.user, desc, 'updated')

            if interview.round == 1:
                submission.status = 'sub'
                interview = self.rank_interviews(interview, 'cancel')

            submission.is_active = True
            submission.save()

            # if interview.guest_type in ['coder', 'assistance']:
            #     title = "Interview cancelled, coding is not required"
                # coder_request_notification(interview, title, request)

            title = f"""CTB:{interview.supervisor.employee_name} :: {interview.round}R ::
                                    {interview.get_screening_type_display()} :: 
                                    {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} :: 
                                    {submission.client} :: {interview.consultant.name} :: 
                                    {interview.marketer.employee_name}"""

            notification_data = {
                'category': 'info', 'description': title,
                'target_id': interview.id, 'parent_id': submission.id,
                'target_type': 'interview', 'parent_type': 'submission',
                'sender_id': request.user.id, 'sender_user_type': 'user',
                'recipient_user_type': 'user', 'title': 'Interview Cancelled',
            }
            user_list, _ = get_users_and_attendees(request, interview)
            create_notification(user_list, notification_data)
            return Response({"message": "Interview cancelled"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, pk):
        try:
            fields, group = list(), None
            interview = get_object_or_404(Interview, id=pk)

            user_ids = get_authenticated_users(request, get_id=True)
            if interview.submission.created_by.id in user_ids:
                group = ObjectGroup.objects.filter(name='owner', model='interview', status=interview.status)

            elif interview.supervisor.id in user_ids:
                group = ObjectGroup.objects.filter(name='supervisor', model='interview', status=interview.status)

            if group:
                fields = group.first().fields.all().values_list('name', flat=True)
            return Response({"data": fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='update_notes')
    def update_notes(self, request, pk):
        try:
            queryset = Interview.objects.filter(
                Q(id=pk) & (Q(submission__created_by=request.user) | Q(supervisor=request.user))
            )
            if queryset:
                interview = queryset.first()
                interview.notes = request.data.get('notes')
                interview.save()

                # Activity
                desc = f"Notes updated on round {interview.round} of Interview by {request.user.employee_name}"
                create_activity(interview.submission.id, 'submission', request.user, desc, 'updated')

                serializer = InterviewCreateSerializer(interview)
                return Response({"data": serializer.data}, status=202)
            else:
                return Response({"message": "You are not allowed to upload"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put', 'delete'], detail=True, url_path='upload_recording')
    def upload_recording(self, request, pk):
        try:
            if request.method == 'PUT':
                file_name = request.data['file_name']
                object_name = f'media/attachments/recordings/{pk}/{file_name}'
                interview = get_object_or_404(Interview, id=pk)
                response, error = presigned_post_url(object_name=object_name)
                if error:
                    return Response({"message": "Unable to upload recording", "error": response}, status=400)
                interview.attachment_link = settings.MEDIA_URL + f'attachments/recordings/{pk}/{file_name}'
                interview.save()

                # Activity
                desc = f"Recording: {file_name} uploaded on round {interview.round} of Interview by " \
                       f"{request.user.employee_name}"
                create_activity(interview.submission.id, 'submission', request.user, desc, 'updated')

                return Response({"data": response, "message": "Recording uploaded"}, status=202)
            else:
                interview = get_object_or_404(Interview, id=pk)
                if interview.attachment_link:
                    file_name = interview.attachment_link.split("/")[-1]
                else:
                    file_name = ""
                interview.attachment_link = None
                interview.save()

                # Activity
                desc = f"Recording: {file_name} deleted from round {interview.round} of Interview by " \
                       f"{request.user.employee_name}"
                create_activity(interview.submission.id, 'submission', request.user, desc, 'updated')

                return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='recording')
    def recording(self, request, pk):
        try:
            from utils_app.aws_utils import get_s3_object
            interview = get_object_or_404(Interview, id=pk)
            if interview.attachment_link:
                response, error = get_s3_object("/".join(interview.attachment_link.split('/')[4:]))
                if error:
                    return Response({"message": "Unable to fetch recording", "error": response}, status=400)
                return Response({"data": response}, status=200)
            return Response({"message": "Recording not available"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='suggestions')
    def interview_suggestions(self, request):
        first, last = get_page_limits(request)
        sub_id = request.GET.get('sub_id')
        ctb = request.GET.get('ctb', None)
        sub = get_object_or_404(Submission, id=sub_id)
        try:
            if ctb:
                queryset = Interview.objects.filter(
                    Q(submission__client__icontains=sub.client) |
                    Q(submission__client__icontains=sub.client, supervisor=ctb) |
                    Q(submission__client__icontains=sub.client,
                      submission__consultant_marketing__consultant=sub.consultant_marketing.consultant) |
                    Q(submission__lead__vendor_company=sub.vendor,
                      submission__consultant_marketing__consultant=sub.consultant_marketing.consultant)
                )
            else:
                queryset = Interview.objects.filter(
                    Q(submission__client__icontains=sub.client) |
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__client__contains=sub.client) |
                    Q(submission__consultant_marketing__consultant=sub.consultant_marketing.consultant,
                      submission__lead__vendor_company=sub.vendor)
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
            return Response({"data": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='repeat')
    def repeat_interviews(self, request):
        try:
            sub_id = request.GET.get('submission_id')
            sub = get_object_or_404(Submission, id=sub_id)
            interviews = Interview.objects.filter(
                submission__client=sub.client,
                submission__lead__city=sub.lead.city,
                submission__lead__position=sub.lead.position
            ).exclude(status='cancelled').exclude(submission=sub).order_by('submission_id', '-created').distinct(
                'submission_id')
            total = interviews.count()
            data = interviews.annotate(
                client=F('submission__client'),
                location=F('submission__lead__city'),
                supervisor_name=F('supervisor__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('submission', 'supervisor_name', 'feedback', 'screening_type', 'client', 'marketer_name', 'status',
                     'consultant_name', 'start_time', 'end_time', 'location', 'company_name', 'interview_mode', )
            return Response({"data": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='assign_guest')
    def assign_guest(self, request, pk):
        try:
            if 'engineer' in request.user.roles:
                queryset = Interview.objects.filter(id=pk)
                if not queryset:
                    return Response({"message": "Interview not found"}, status=404)

                interview = queryset.first()
                guest = request.data.get('guest', [])
                if guest:
                    interview.guest.clear()
                    interview.guest_type = 'assigned'
                    interview.save()

                for user_id in guest:
                    interview.guest.add(user_id)

                est = pytz.timezone('US/Eastern')
                today = datetime.now().astimezone(est)

                # if today.date() < interview.start_time.date():
                #     coder_request_notification(interview, "Coding Assignment", request)

                # if today.date() == interview.start_time.date() and today.time() < interview.start_time.time():
                #     coder_request_notification(interview, "Coding Assignment", request)

                title = get_interview_title(interview)
                _, attendees = get_users_and_attendees(request, interview)

                end_time = datetime.strptime(str(interview.end_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")
                start_time = datetime.strptime(str(interview.start_time), "%Y-%m-%d %H:%M:%S+00:00").strftime(
                    "%Y-%m-%dT%H:%M:%S")

                event = {
                    "end": end_time,
                    "summary": title,
                    "start": start_time,
                    "user": request.user,
                    "attendees": attendees,
                    "lead": interview.submission.lead,
                    "submission": interview.submission,
                    "description": interview.description,
                    "call_details": interview.call_details,
                    "consultant": interview.submission.consultant,
                }

                # Updating calendar Booking
                booking_res = 'Development Server'
                if os.environ.get('ENV', 'local') == 'prod':
                    calendar_id = interview.calendar_id
                    calendar = GoogleCalendar()
                    if not calendar_id:
                        res, msg = calendar.book_calendar(event, interview.submission.created_by.email, request)
                        if msg == 'error':
                            return Response({"message": "Calendar booking failed", "error": res}, status=400)
                        booking_res = 'booked'
                        interview.calendar_id = res['id']
                        interview.save()
                    else:
                        booking_res = 'updated'
                        calendar_mail_id = interview.submission.created_by.email
                        if interview.if_previous_calendar:
                            calendar_mail_id = "suman.m@consultadd.com"
                        res, msg = calendar.update_calendar(calendar_id, event, calendar_mail_id, request)
                        if msg == 'booked':
                            booking_res = 'booked'
                            interview.calendar_id = res['id']
                            interview.save()
                        if msg == "error":
                            return Response({"message": "Calendar update failed", "error": res}, status=400)

                # Activity
                desc = f"{request.user.employee_name} added coder experts"
                create_activity(interview.id, 'submission', request.user, desc, 'updated')

                return Response({"data": "Coders assigned", "booking_response": booking_res}, status=202)
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='guest_feedback')
    def guest_feedback(self, request, pk):
        try:
            queryset = Interview.objects.filter(id=pk, guest__in=[request.user])
            if not queryset:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
            interview = queryset.first()
            interview.coding_present = True if request.data.get('coding_present') == 'true' else False
            interview.guest_remark = request.data.get('feedback', None)
            interview.save()

            ques_answers = create_answer(request, interview, 'interview')
            if not ques_answers:
                return Response({"message": "No feedback given"}, status=400)

            # Activity
            desc = f"{request.user.employee_name} provided coding feedback for Interview I-{interview.id}"
            create_activity(interview.submission.id, 'submission', request.user, desc, 'updated')

            return Response({"message": "Coding Feedback Submitted"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='feedback_questions')
    def feedback_questions(self, request):
        try:
            data = [
                "Coding Language?",
                "How many questions were there ?",
                "Were you able to solve the questions ?",
            ]
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['post', 'put'], detail=True, url_path='supervisor_feedback')
    def feedback(self, request, pk):
        try:
            if request.method == 'POST':
                interview = get_object_or_404(Interview, id=pk)

                ques_answers = create_answer(request, interview, 'interview')
                if not ques_answers:
                    return Response({"message": "No feedback given"}, status=400)

                # Activity
                desc = f"{request.user.employee_name} provided supervisor feedback for Interview I-{interview.id}"
                create_activity(interview.submission.id, 'submission', request.user, desc, 'created')

                return Response({"message": "Feedback submitted"}, status=201)
            else:
                prev_feedback = []
                interview = get_object_or_404(Interview, id=pk)
                answers = Answer.objects.filter(
                    object_id=interview.id, content_type__model='interview',
                    question__form_name=request.GET.get("form_name", "interview")
                ).values('id')
                for ans in answers:
                    prev_feedback.append(ans['id'])
                ques_answers = create_answer(request, interview, 'interview')
                if not ques_answers:
                    return Response({"message": "No feedback given"}, status=400)

                for value in prev_feedback:
                    answer = get_object_or_404(Answer, id=value)
                    answer.delete()

                # Activity
                desc = f"{request.user.employee_name} updated supervisor feedback for Interview I-{interview.id}"
                create_activity(interview.submission.id, 'submission', request.user, desc, 'created')

                if interview.status in ['passed', 'next_round', 'failed']:
                    slack_card_json = interview_feedback_card(interview, request)
                    post_msg_using_webhook(config.slack_interview_feedback_url, slack_card_json)
                return Response({"message": "Feedback updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='reasons')
    def reason(self, request):
        try:
            passed_reasons = Interview.PASSED_CHOICES
            failed_reasons = Interview.FAILURE_CHOICES
            is_active = request.query_params.get('is_active', False)
            if not is_active:
                failed_reasons_list = list(failed_reasons)
                failed_reasons_list.append(('hired_else', 'Hired Someone Else'))
                return Response(
                    {"passed_reasons": passed_reasons, "failure_reasons": tuple(failed_reasons_list)}, status=200
                )
            return Response({"passed_reasons": passed_reasons, "failure_reasons": failed_reasons}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='remind_me_later')
    def remind_me_later(self, request):
        try:
            content_type = ContentType.objects.get(model='interview')
            notification = UserNotification.objects.filter(user=request.user.id,content_type=content_type).first()
            interviews = Interview.objects.filter(status="feedback_due", supervisor=request.user.id).all()
            if interviews:
                notification.count += 1
                notification.save()
                if notification.count < 3:
                    schedule_push_notification.delay(request.user.id,notification.count)
            else:
                if notification:
                    notification.delete()
            return Response({"message":"Done"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='supervisor_feedback_due')
    def supervisor_feedback_due(self, request,pk):
        try:
            interviews = Interview.objects.filter(status="feedback_due", supervisor=pk)
            content_type = ContentType.objects.get(model='interview')
            notification = UserNotification.objects.filter(user=pk,is_active=True,content_type=content_type).first()
            feedback_due_list = []
            if notification:
                notification.is_active = False
                notification.save()
                for interview in interviews:
                    feedback_due = {
                        "round": interview.round,
                        "schedule": interview.end_time,
                        "client": interview.submission.client,
                        "position": interview.submission.lead.position.name,
                        "consultant_name": interview.submission.consultant_marketing.consultant.name
                    }
                    feedback_due_list.append(feedback_due)

            return Response({"data": {"count": notification.count if notification else 0,"interview": feedback_due_list}},status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /test/
class TestViewSets(GenericViewSet, CreateModelMixin, ListModelMixin, UpdateModelMixin):
    queryset = Test.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TestCreateSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_count_and_queryset(queryset, filter_by_status, sort_by):
        try:
            # Interview counts by status
            queryset = queryset.order_by('id').distinct('id')
            data_counts = {
                'total': queryset.count(),
                'new': queryset.filter(status='new').count(),
                'failed': queryset.filter(status='failed').count(),
                'passed': queryset.filter(status='passed').count(),
                'assigned': queryset.filter(status='assigned').count(),
                'cancelled': queryset.filter(status='cancelled').count(),
                'feedback_due': queryset.filter(status='feedback_due').count(),
            }

            if filter_by_status:
                queryset = queryset.filter(status__in=filter_by_status)

            if sort_by in ['created', 'modified', 'deadline']:
                order_by = f"-{sort_by}"
            else:
                order_by = '-created'
                if filter_by_status == 'failed':
                    order_by = '-modified'

            queryset = Test.objects.filter(id__in=queryset.values('id')).order_by(order_by)
            return queryset, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    @staticmethod
    def send_test_mail(test, data, test_status, request):
        try:
            consultant = test.submission.consultant
            queryset = User.objects.filter(
                team=test.submission.marketing_team, role__name__in=['admin', 'proxy'], is_active=True
            )
            path = []
            created_by = test.submission.created_by
            scrum_masters = [user.email for user in queryset]
            skills = ", ".join(skill.title() for skill in test.skills)
            if test_status == 'new':
                test_type = 'Online'
                if data['is_video'] == 'True':
                    test_type = "Video"
                if data['is_offline'] == 'True':
                    test_type = 'Offline'
                to = [config.ENGINEERING]
                cc = [created_by.email] + scrum_masters
                subject = f'Test :: TST-{test.id} :: {test_type} :: {consultant.name} :: {skills} '
                resume = test.submission.attachments.filter(attachment_type='resume')
                if resume:
                    response, error = download_s3_object(resume.first().attachment_file.name)
                    if not error:
                        path.append(response)
                test_docs = test.attachments.all()
                for doc in test_docs:
                    response, error = download_s3_object(doc.attachment_file.name)
                    if not error:
                        path.append(response)
                deadline = datetime.strptime(test.deadline, "%Y-%m-%d").strftime(
                    "%b. %d, %Y") if test.deadline else 'NA'
                mail_data = {
                    'subject': subject,
                    'to': to, 'cc': cc, 'bcc': [],
                    'template': '../templates/test_mail.html',
                    'context': {
                        'skills': skills,
                        'deadline': deadline,
                        'consultant': consultant.name,
                        'marketer_email': created_by.email,
                        'consultant_email': consultant.email,
                        'city': test.submission.current_city,
                        'visa_end': test.submission.visa_end,
                        'dob': test.submission.date_of_birth,
                        'marketer': created_by.employee_name,
                        'visa_type': test.submission.visa_type,
                        'consultant_phone': consultant.phone_no,
                        'visa_start': test.submission.visa_start,
                        'marketing_email': test.submission.email,
                        'marketing_phone': test.submission.phone,
                        'job_title': test.submission.lead.job_title,
                        'test_link': data['link'] if data['link'] else 'NA',
                        'is_video': 'Yes' if data['is_video'] == 'True' else 'No',
                        'vendor_company': test.submission.lead.vendor_company.name,
                        'is_offline': 'Yes' if data['is_offline'] == 'True' else 'No',
                        'jd': test.submission.lead.job_desc.replace("\n", " ;newline; "),
                        'con_informed': 'Yes' if data['con_informed'] == 'True' else 'No',
                        'client': test.submission.client if test.submission.client else 'NA',
                        'con_timezone': data['con_timezone'] if data['con_timezone'] else 'NA',
                        'additional_details': data['additional_details'].replace("\n", " ;newline; ") if data[
                            'additional_details'] else 'NA',
                    },
                    'attachments': path
                }
                res, msg, from_mail = send_email_attachment_multiple(mail_data, created_by.email, request=request)
                delete_temp_file(path)
                if not msg:
                    return res, "error"
                content_type = ContentType.objects.get(model="test")
                mail_object = MapMail(mail_id=res, object_id=test.id, content_type=content_type, from_mail_id=from_mail)
                mail_object.save()
                return res, "ok"

            elif test_status == 'submit':
                test_type = 'Online'
                if test.is_video:
                    test_type = "Video"
                if test.is_offline:
                    test_type = 'Offline'
                engineers_email = [user.email for user in test.engineer.all()]
                engineers_email.append(test.submitted_by.email)
                if test.engineer.all():
                    engineer = ", ".join(engineer.employee_name for engineer in test.engineer.all())
                else:
                    engineer = 'NA'
                for answer in data['ques_answers']:
                    if answer['answer'] == 'submitted':
                        ans = Answer.objects.get(id=answer['id'])
                        test_docs = ans.attachment.filter(attachment_type='test_feedback')
                        answer['answer'] = len(test_docs)
                        for doc in test_docs:
                            response, error = download_s3_object(doc.attachment_file.name)
                            path.append(response)

                to = [created_by.email]
                title = f"Test Completed"
                cc = scrum_masters + [config.ENGINEERING] + engineers_email
                subject = f'Test Completed :: TST-{test.id} :: {test_type} :: {consultant.name} :: {skills}'
                single_question, parent_question = structure_mail_data(data['ques_answers'])
                mail_data = {
                    'to': to, 'cc': cc, 'bcc': [],
                    'subject': subject, 'attachments': path,
                    'template': '../templates/submit_engineer_feedback.html',
                    'context': {
                        'parent_question': parent_question,
                        'engineer': engineer, 'title': title,
                        'rate_performance': data['rate_performance'],
                        'single_question': single_question, 'remarks': test.engineer_remarks,
                    },
                }
                # Need to filter on based one type and objectId
                mail_id = None
                from_mail = test.submitted_by.email
                email_object = MapMail.objects.filter(content_type__model="test", object_id=test.id).first()
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

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        sort_by = request.GET.get('sort_by', None)
        filter_for = request.GET.get('filter_for', 'all')
        filter_json = request.GET.get('filter_json', None)
        export = json.loads(request.GET.get('export', 'false'))
        filter_by_status = request.GET.get('filter_by_status', None)

        try:
            roles = request.user.roles

            # Search Test by Client, VendorContact, Consultant and Marketer
            if query:
                query = query.lstrip().replace(':amp:', '&')
                if query.isnumeric():
                    queryset = Test.objects.filter(
                        Q(id__exact=query) |
                        Q(submission__client__istartswith=query) |
                        Q(submission__created_by__employee_name__istartswith=query) |
                        Q(submission__lead__vendor_company__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__email__istartswith=query)
                    )
                else:
                    queryset = Test.objects.filter(
                        Q(submission__client__istartswith=query) |
                        Q(submission__created_by__employee_name__istartswith=query) |
                        Q(submission__lead__vendor_company__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__name__istartswith=query) |
                        Q(submission__consultant_marketing__consultant__email__istartswith=query)
                    )
            else:
                queryset = Test.objects.exclude(status='archive')

            if filter_for == 'my':
                if 'engineer' in roles:
                    queryset = queryset.filter(
                        Q(engineer=request.user) | Q(assign_to=request.user) | Q(submission__created_by=request.user)
                    )
                else:
                    queryset = queryset.filter(submission__created_by=request.user)

            elif filter_for == 'handover':
                users = get_authenticated_users(request)
                users.remove(request.user)
                queryset = queryset.filter(submission__created_by__in=users)

            elif filter_for == 'team' and 'admin' in roles:
                if 'engineer' in roles:
                    queryset = queryset.filter(engineer__team=request.user.team)
                else:
                    queryset = queryset.filter(Q(submission__marketing_team__in=request.user.associated_to) |
                                               Q(submission__marketing_team=request.user.team))

            # Test List according to role
            if ('admin' in roles and 'engineer' in roles) or 'superadmin' in roles:
                pass
            elif 'admin' in roles or 'proxy' in roles:
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

            if filter_json:
                filter_by_status = list()
                filters = json.loads(filter_json)

                if 'status' in filters and len(filters["status"]) > 0:
                    filter_by_status = filters["status"]

                if 'client' in filters and len(filters["client"]) > 0:
                    queryset = queryset.filter(submission__client__in=filters['client'])

                if 'platform' in filters and len(filters["platform"]) > 0:
                    queryset = queryset.filter(
                        Q(engineer_feedback__answer__in=filters["platform"]) | Q(platform__in=filters['platform']))

                if 'marketer' in filters and len(filters["marketer"]) > 0:
                    queryset = queryset.filter(submission__created_by_id__in=filters['marketer'])

                if 'vendor' in filters and len(filters["vendor"]) > 0:
                    queryset = queryset.filter(submission__lead__vendor_company__name__in=filters['vendor'])

                if 'deadline' in filters and filters.get('deadline', None):
                    queryset = queryset.filter(deadline__lte=filters.get('deadline'))

                if 'consultant' in filters and len(filters["consultant"]) > 0:
                    queryset = queryset.filter(
                        submission__consultant_marketing__consultant__name__in=filters['consultant'])

                created = filters.get('created', None)
                queryset = date_filter(queryset, created, 'created')

            queryset, counts = self.get_count_and_queryset(queryset, filter_by_status, sort_by)
            if counts == 'error':
                return Response({"error": str(queryset)}, status=400)

            url = ""
            if export:
                file_name = f"test_report_{datetime.now().strftime('%d-%B-%Y')}.csv"
                file = open(file_name, 'w')
                writer = csv.writer(file)
                writer.writerow(['Test Id', 'Consultant Name', 'Marketer Name', 'Client', 'Job Title', 'Company Name',
                                 'Link', 'Created At', 'Deadline', 'Skills', 'Submitted By', 'Status',
                                 'Marketer Feedback', 'Engineer Associated'])
                for obj in queryset:
                    engineer_associated = [obj.employee_name for obj in obj.engineer.all()]
                    writer.writerow([
                        obj.id, obj.submission.consultant.name, obj.submission.created_by.employee_name,
                        obj.submission.client, obj.submission.lead.job_title, obj.submission.lead.vendor_company.name,
                        obj.link, obj.created.date(), obj.deadline, obj.skills,
                        obj.submitted_by.employee_name if obj.submitted_by else None, obj.get_status_display(),
                        obj.feedback, engineer_associated
                    ])
                file.close()
                url = generate_s3_url(file_name)

            data = TestListSerializer(queryset[first:last], many=True).data
            return Response({"counts": counts, "data": data, "url": url}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            users = get_authenticated_users(request)
            submission = get_object_or_404(Submission, id=request.data.get('submission'), created_by__in=users)
            if not submission:
                return Response({"error": 'This is not your submission'}, status=400)
            if submission.test.filter(status__in=['new', 'assigned', 'feedback_due']):
                return Response(
                    {"message": "Submit the feedback of previous test on this submission before creating a new test"},
                    status=400
                )

            is_video, is_offline, con_informed = False, False, False

            if request.data.get('is_video', 'false') == "True":
                is_video = True
            if request.data.get('is_offline', 'false') == "True":
                is_offline = True
            if request.data.get('con_informed', 'false') == "True":
                con_informed = True

            data = {
                "is_video": is_video,
                "is_offline": is_offline,
                "con_informed": con_informed,
                "link": request.data.get('link', None),
                "deadline": request.data.get('deadline', None),
                "skills": json.loads(request.data.get('skills')),
                "con_timezone": request.data.get('con_timezone', 'NA'),
                "additional_details": request.data.get('additional_details', None),
            }
            test = Test.objects.create(
                status='new',
                link=data['link'],
                skills=data['skills'],
                submission=submission,
                deadline=data['deadline'],
                is_video=data['is_video'],
                is_offline=data['is_offline'],
                platform=request.data.get('platform', None),
                additional_details=data['additional_details'],
            )

            if test.platform:
                test_platform(request, test.platform)
            # Activity
            if is_video:
                desc = f"Video test created with deadline {str(test.deadline)}"
            elif is_offline:
                desc = f"Offline test created with deadline {str(test.deadline)}"
            else:
                desc = f"Test created with deadline {str(test.deadline)}"
            create_activity(submission.id, 'submission', request.user, desc, 'created')

            # upload attachments
            for file in request.FILES.getlist('files'):
                file_data = {
                    "file": file,
                    "type": 'test',
                    "model": "test",
                    "object_id": test.id,
                    "creator": request.user,
                }
                create_attachment(file_data)

            # Test email to engineering team
            test_received_notification(test, data.get('con_timezone', 'NA'), request)
            res, error = self.send_test_mail(test, data, 'new', request)
            if error == 'error':
                write_info(message=res, function='create-send_test_mail', request=request)
                return Response({"message": "Test created but mail not sent", "error": str(res)}, status=400)
            serializer = TestCreateSerializer(test)
            return Response({"data": serializer.data, "mail": res, "message": "Test created and mail sent"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            users = get_authenticated_users(request)
            test = get_object_or_404(Test, id=kwargs.get('pk'), submission__created_by__in=users)
            prev_platform = test.platform
            new_platform = request.data.get('platform', prev_platform)
            if prev_platform != new_platform:
                test_content_type = ContentType.objects.get(model='test')
                available_platforms = Choice.objects.filter(
                    content_type=test_content_type, field='platform',
                    display_name__icontains=test.platform, name__icontains=test.platform
                )
                if not available_platforms.first() and test.platform != 'Not Available':
                    Choice.objects.create(
                        content_type=test_content_type, name=test.platform, field='platform', display_name=test.platform
                    )
            serializer = TestUpdateSerializer(test, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Activity
                desc = f"Test details updated"
                create_activity(test.submission.id, 'submission', request.user, desc, 'created')

                return Response({"data": serializer.data, "message": "Test updated"}, status=202)
            else:
                return Response({"message": ERROR_MSG, "error": serializer.errors}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['get'], detail=True, url_path='fields')
    def fields(self, request, pk):
        try:
            users = get_authenticated_users(request)
            test = get_object_or_404(Test, id=pk, submission__created_by__in=users)
            fields, group = [], None

            authentic_users = list()
            authentic_users.append(test.submitted_by)
            authentic_users.extend(test.engineer.all())
            authentic_users.extend(test.assign_to.all())
            result = set(users).intersection(set(authentic_users))
            if result:
                group = ObjectGroup.objects.filter(name='assigned', model='test', status=test.status)

            if test.submission.created_by in users:
                group = ObjectGroup.objects.filter(name='owner', model='test', status=test.status)

            if group:
                fields = group.first().fields.all().values_list('name', flat=True)
            return Response({"data": fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='test_status')
    def test_status(self, request):
        try:
            return Response({"result": Test.STATUS_CHOICES}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='test_platform')
    def test_platform(self, request):
        try:
            platforms = Question.objects.get(title="Platform", form_name='online_test')
            return Response(platforms.options, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='assign')
    def assign_test(self, request, pk):
        try:
            test = get_object_or_404(Test, id=pk)
            users = request.data.get('assign_to', [])
            test.assign_to.clear()
            user_list, user_names = [], []
            for user_id in users:
                user = get_object_or_404(User, id=user_id)
                test.assign_to.add(user)
                user_list.append(user)
                user_names.append(user.employee_name)

            test.status = 'assigned'
            test.save()
            submission = test.submission

            # Activity
            desc = f"{request.user.employee_name} assigned test to {', '.join(user_names)}"
            create_activity(test.submission.id, 'submission', request.user, desc, 'created')

            # notification
            skills = ", ".join(skill.title() for skill in test.skills)
            test_type = 'Online'
            if test.is_video:
                test_type = "Video"
            if test.is_offline:
                test_type = 'Offline'

            title = f"Test assigned :: {submission.consultant.name} :: {submission.client} :: {test_type} :: {skills}"
            notification_data = {
                'title': title,
                'category': 'info',
                'description': title,
                'target_id': test.id,
                'target_type': 'test',
                'sender_user_type': 'user',
                'parent_type': 'submission',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
                'parent_id': submission.id,
            }
            create_notification(user_list, notification_data)

            # Push Notification
            message_body = {
                "title": title, "category": "alert",
                "body": title, "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "data": {
                    'target_id': test.id, 'timestamp': str(datetime.now()),
                    'is_read': False, 'target': 'test', 'is_deleted': False,
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            # message to channel
            current_time = datetime.strftime(datetime.utcnow(), "%H:%M:%S")
            if "14:30:00" < current_time < "23:30:00":
                consultant_name = submission.consultant.name
                assigned = ", ".join(assigned.employee_name for assigned in test.assign_to.all())
                text = f"Test Assigned to :- {assigned} <br>"
                payload = {
                    "title": text,
                    "body": f"&#128203; Test Assigned :: {consultant_name} :: {submission.client} :: {skills}"
                }
                # data = MessageCard.get_simple_card(payload)
                # post_msg_using_webhook(config.slack_engineering_url, data)

            serializer = TestCreateSerializer(test)
            return Response({"data": serializer.data, "message": "Test assigned"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='submit')
    def submit_test(self, request, pk):
        try:
            test = get_object_or_404(Test, id=pk)
            data = {
                'engineer': json.loads(request.data.get('engineer')),
                'remarks': request.data.get('remarks', None),
            }
            for engineer_id in data['engineer']:
                engineer = get_object_or_404(User, id=engineer_id)
                test.engineer.add(engineer)

            test.status = 'feedback_due'
            test.submitted_by = request.user
            test.submit_date = datetime.now()
            test.engineer_remarks = data['remarks']
            test.save()

            # Activity
            desc = f"{request.user.employee_name} completed test and submitted"
            create_activity(test.submission.id, 'submission', request.user, desc, 'created')

            # upload attachments
            for file in request.FILES.getlist('file'):
                file_data = {
                    "file": file,
                    "model": "test",
                    "type": 'test_submit',
                    "object_id": test.id,
                    "creator": request.user,
                }
                create_attachment(file_data)
            # test submit mail
            res = "Development Server"
            # if os.environ.get('ENV', 'local') == 'prod':
            res, error = self.send_test_mail(test, data, 'submit', request)
            if error == 'error':
                write_info(message=res, function='create-send_test_mail', request=request)
                return Response({"message": "Test submitted but mail not sent", "error": str(res)}, status=400)
            serializer = TestCreateSerializer(test)
            return Response({"data": serializer.data, "mail": res, "message": "Test submitted"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='feedback')
    def submit_test_feedback(self, request, pk):
        try:
            users = get_authenticated_users(request)
            test = get_object_or_404(Test, id=pk, submission__created_by__in=users)
            test.feedback = request.data.get('feedback')
            test.status = request.data.get('status')
            test.submitted_by = request.user
            test.save()
            assigned_test_points(test,request)
            # Activity
            desc = f"Test status updated to {test.get_status_display()} by {request.user.employee_name}"
            create_activity(test.submission.id, 'submission', request.user, desc, 'update')

            file = request.FILES.get('file')
            if file:
                file_data = {
                    "file": file,
                    "model": "test",
                    "object_id": test.id,
                    "creator": request.user,
                    "type": 'test_feedback',
                }
                create_attachment(file_data)

            # App Notification
            user_list = [user for user in test.engineer.all()]
            user_list.append(test.submitted_by)
            title = f"Feedback Added for Test :: {test.submission.consultant.name}"

            notification_data = {
                'title': title,
                'category': 'alert',
                'description': title,
                'target_type': 'user',
                'sender_user_type': 'user',
                'parent_type': 'submission',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
                'parent_id': test.submission.id,
                'target_id': test.submitted_by.id,
            }
            create_notification(user_list, notification_data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "data": {
                    'target': 'test',
                    'is_read': False,
                    'is_deleted': False,
                    'target_id': test.id,
                    'timestamp': str(datetime.now()),
                },
            }

            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            serializer = TestCreateSerializer(test)
            return Response({"data": serializer.data, "message": "Test feedback added"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=True, url_path='engineer_feedback')
    def feedback(self, request, pk):
        try:

            test = get_object_or_404(Test, id=pk)
            engineers = json.loads(request.data.get('associates', '[]'))
            for emp_id in engineers:
                engineer = User.objects.get(employee_id=emp_id)
                test.engineer.add(engineer)

            ques_answers = create_answer(request, test, 'test')
            if not ques_answers:
                return Response({"message": "No feedback given"}, status=400)
            test.status = 'feedback_due'
            test.submitted_by = request.user
            test.submit_date = datetime.now()
            test.engineer_remarks = request.data.get('remarks')
            if not test.engineer_feedback.all():
                return Response({"message": "Please submit engineer's feedback again"}, status=400)
            test.save()

            # Activity
            desc = f"{request.user.employee_name} completed test TST-{test.id} and submitted engineer feedback"
            create_activity(test.submission.id, 'submission', request.user, desc, 'created')

            rate_performance = {}
            for question in ques_answers:
                if question['question'] == 'Rate your performance':
                    rate_performance = question
                    ques_answers.remove(question)
            data = {
                'ques_answers': ques_answers,
                'rate_performance': rate_performance,
            }
            # test submit mail
            res, error = self.send_test_mail(test, data, 'submit', request)
            if error == 'error':
                write_info(message=res, function='create-send_test_mail', request=request)
                return Response({"message": "Test submitted but mail not sent", "error": str(res)}, status=400)

            return Response({"message": "Feedback submitted", "mail": res}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /question/
class QuestionViewSets(ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            question_field = request.GET.get("form_name", None)
            queryset = Question.objects.filter(
                form_name=question_field, is_active=True, category__in=['basic', 'generic', 'guideline']
            ).order_by('position')
            serializer = QuestionSerializer(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            if 'superadmin' not in request.user.roles:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            if data.get('type') == 'option' and data.get('options') is []:
                return Response({"message": "Please provide possible options for the question value"})

            if data.get('position'):
                position = data.get('position')
                question_qs = Question.objects.filter(
                    form_name=data.get('form_name'), position__gte=position, category=data.get('category')
                ).order_by('position')
                for obj in question_qs:
                    obj.position += 1
                    obj.save()
            else:
                question_qs = Question.objects.filter(
                    category=data.get('category'), form_name=data.get('form_name')
                ).order_by('position').last()
                position = question_qs.position + 1

            Question.objects.create(
                position=position,
                title=request.data.get('title'),
                category=request.data.get('category'),
                form_name=request.data.get('form_name'),
                options=request.data.get('options', []),
                answer_type=request.data.get('type', 'text'),
                description=request.data.get('description', None),
                placeholder=request.data.get('placeholder', None),
            )

            return Response({"message": "Question added to form"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='parent')
    def parent(self, request, pk):
        try:
            qs = Question.objects.filter(id=pk)
            if qs:
                question = qs.first()
            else:
                return Response({"message": ERROR_MSG, "error": "Question not found"}, status=400)

            value = request.GET.get('value', None)
            if not value:
                return Response({"message": "value is empty"}, status=400)
            no_of_questions = int(value)
            cq = question.child_question.first()
            if cq:
                questions = cq.child_question.all().order_by('position')[:no_of_questions]
                serializer = ParentQuestionSerializer(questions, many=True)
                return Response({"data": serializer.data}, status=200)
            return Response({"message": ERROR_MSG, "error": "Child question not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /marketing_team/
class MarketingTeamViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = Team.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamStructureSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_assign_consultant(obj):
        consultants = obj.marketed.filter(status='open')
        if consultants:
            data = {
                "count": len(consultants),
                "consultant": [{
                    "id": consultant.consultant.id, "consultant_name": consultant.consultant.name
                } for consultant in consultants]
            }
            return data
        return []

    @staticmethod
    def get_current_offers(obj):
        offers = obj.submissions.filter(status__in=['project'])
        if offers:
            data = {
                "count": len(offers),
                "project": [{
                    "id": offer.id, "client": offer.client
                } for offer in offers]
            }
            return data
        return []

    def filter_marketers(self, queryset, filters, request):
        try:
            marketer_data = []
            scrum_master, scrum_id = None, ""
            shifts = User.SHIFT_CHOICE
            eng_teams = Team.objects.filter(dept='Marketing')
            inter_section = request.GET.get('inter_section', None)

            if filters:
                if "skills" in filters:
                    if inter_section == "true":
                        queryset = queryset.filter(technology__contains=filters["skills"])
                    else:
                        queryset = queryset.filter(technology__overlap=filters['skills'])
                if "shifts" in filters:
                    queryset = queryset.filter(shift__in=filters['shifts'])
                if "teams" in filters:
                    queryset = queryset.filter(team__id__in=filters['teams'])
            scrum_master = queryset.filter(role__name__iexact='admin').first()
            if scrum_master:
                scrum_id = scrum_master.id
            for obj in queryset:
                assign_consultant = self.get_assign_consultant(obj)
                current_offers = self.get_current_offers(obj)
                data = {
                    "id": obj.id, "employee_id": obj.employee_id, "employee_name": obj.employee_name,
                    "assign_consultant": assign_consultant, "team": obj.team.name, "is_scrum": False,
                    "shift": obj.get_shift_display(), "technology": obj.technology, "current_offers": current_offers
                }
                if obj.id == scrum_id:
                    data["is_scrum"] = True
                    scrum_master = data
                    continue
                marketer_data.append(data)
            if scrum_master:
                marketer_data.insert(0, scrum_master)
            counts = {
                "shift": [
                    {
                        "name": shift[0],
                        "display_name": shift[1],
                        "count": queryset.filter(shift=shift[0]).exclude(shift=None).count()
                    }
                    for shift in shifts
                ],
                "team": [
                    {
                        "id": team.id,
                        "display_name": team.name,
                        "count": queryset.filter(team=team).exclude(team=None).count()
                    }
                    for team in eng_teams
                ],
                "skill": [
                    {
                        "display_name": technology,
                        "count": queryset.filter(technology__overlap=[technology]).count()
                    }
                    for technology in TECHNOLOGIES
                ]
            }
            return marketer_data, counts
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def list(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filters = json.loads(request.GET.get('filter_json', '{}'))
            marketers = User.objects.filter(team__dept='Marketing', is_active=True)
            if query:
                marketers = marketers.filter(employee_name__istartswith=query)
            marketers_data, counts = self.filter_marketers(marketers, filters, request)
            return Response({"data": marketers_data[first: last], "count": counts, "total": len(marketers_data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            data = {
                "count": team.employees.filter(is_active=True).count(),
                "id": team.id, "name": team.name, "scrum_timing": team.scrum_timing
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            if 'superadmin' not in request.user.roles and 'admin' not in request.user.roles:
                return Response({"message": "You don't have access"}, status=400)

            data = request.data
            name = data['name'].replace(' ', '')
            team = Team.objects.filter(name__iexact=name)
            if team:
                return Response({"message": "Team name already in use"}, status=400)
            Team.objects.create(name=data['name'], scrum_timing=data['scrum_timing'],
                                dept='Marketing', email='engineering@consultadd.com')
            return Response({"message": "Team added to log1"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            name = request.data['name'].replace(' ', '')
            existing_team = Team.objects.filter(name__iexact=name)
            if existing_team:
                return Response({"message": "Team name already in use"}, status=400)
            serializer = TeamSerializer(team, data=request.data, partial=True)
            serializer.is_valid()
            serializer.save()

            # Activity
            desc = f"{request.user.employee_name} update {team.name} details."
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response({"message": "Team Details Updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    # @action(methods=['get'], detail=False, url_path='export')
    # def export(self, request, **kwargs):
    #     try:
    #         query = request.GET.get('query', None)
    #         filters = json.loads(request.GET.get('filter_json', '{}'))
    #         marketers = User.objects.filter(role__name='marketer', is_active=True)
    #         if query:
    #             marketers = marketers.filter(employee_name__istartswith=query)
    #         marketers, counts = self.filter_marketers(marketers, filters, request)
    #         serializer = TeamStructureSerializer(marketers, many=True)
    #         if serializer.data:
    #             file_url = get_team_structure_xlsx(serializer.data, counts, request)
    #             return Response({"data": file_url}, status=200)
    #         return Response({"message": "No Data to export"}, status=400)
    #     except Exception as error:
    #         write_exception(error, request)
    #         return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=False, url_path='update_shift')
    def shift(self, request, **kwargs):
        try:
            shift = request.data.get('shift', None)
            employee_ids = request.data.get('employee_ids', [])
            if not employee_ids or not shift:
                return Response({"message": "Data not provided"}, status=400)
            for emp_id in employee_ids:
                employee = get_object_or_404(User, id=emp_id)
                employee.shift = shift
                employee.save()
            return Response({"message": "Shift Detail Updated"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='teams')
    def teams(self, request, **kwargs):
        try:
            team_data = []
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            teams = Team.objects.filter(dept='Marketing').order_by('-id')
            if query:
                teams = teams.filter(name__istartswith=query.lstrip().replace(':amp:', '&'))
            for team in teams[first: last]:
                data = {
                    "count": team.employees.filter(is_active=True).count(),
                    "id": team.id, "name": team.name, "scrum_timing": team.scrum_timing,
                    "scrum_master": team.employees.filter(role__name='admin', is_active=True).values(
                        'id', 'employee_name')
                }
                team_data.append(data)

            return Response({"data": team_data, "total": len(teams)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='compare_teams')
    def compare_team(self, request):
        try:
            team_data = []
            team_ids = request.GET.get("team_ids", '')
            if team_ids:
                team_ids = team_ids.split(',')
            teams = Team.objects.filter(dept='Marketing', id__in=team_ids).order_by('-id')
            for team in teams:
                data = {
                    "id": team.id, "team_name": team.name,
                    "employee": team.employees.filter(is_active=True).exclude(role__name='admin').values('id', 'employee_name'),
                    "scrum": team.employees.filter(
                        is_active=True, role__name='admin').values('id', 'employee_name')
                }
                team_data.append(data)

            return Response({"data": team_data, "total": len(teams)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=True, url_path='move_employee')
    def move_employee(self, request, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            employee_ids = request.data.get('employee_ids', [])
            if not employee_ids or not team:
                return Response({"message": "Data not provided"}, status=400)

            scrum_masters, employee_added = [], []
            for emp_id in employee_ids:
                employee = get_object_or_404(User, id=emp_id)
                if employee.role.filter(name='admin'):
                    scrum_masters.append(employee.employee_name)
                    continue
                employee_added.append(employee.employee_name)
                employee.team = team
                employee.save()

            # Activity
            employees = ", ".join(emp for emp in employee_added)
            desc = f"{request.user.employee_name} added {employees} to {team.name}"
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response({"message": "Marketers moved successfully", "not_moved": scrum_masters}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=True, url_path='update_scrum')
    def update_scrum(self, request, **kwargs):
        try:
            if 'superadmin' not in request.user.roles:
                return Response({"message": "You do not have access to perform this action"}, status=200)
            team_id = kwargs.get('pk')
            employee_id = request.data.get('employee_id', None)
            if not employee_id:
                return Response({"message": "No employee selected"}, status=200)
            scrum_role = Role.objects.get(name='admin')
            employee = get_object_or_404(User, id=employee_id, team_id=kwargs.get('pk'))
            prev_scrum = User.objects.filter(team_id=team_id, role=scrum_role)
            if prev_scrum:
                prev_scrum.first().role.remove(scrum_role)
            employee.role.add(scrum_role)

            # Activity
            desc = f"{request.user.employee_name} made {employee.employee_name} as scrum master for {employee.team.name}"
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response(
                {"message": f"{employee.employee_name} appointed as scrum master for {employee.team.name}"}, status=202
            )
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['delete'], detail=True, url_path='remove_team')
    def remove(self, request, pk):
        try:
            team = get_object_or_404(Team, id=pk)
            team_employees = User.objects.filter(team=team)
            team_name = team.name
            if team_employees:
                return Response({"message": f"Some employees still associated to {team_name}"}, status=400)
            team.delete()

            # Activity
            desc = f"{request.user.employee_name} removed team {team_name}"
            create_activity(pk, 'team', request.user, desc, 'deleted')
            return Response({"message": "Team Removed Successfully"}, status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)


class MarketingAPIViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = Test.objects.all()
    serializer_class = TestUpdateSerializer

    @action(methods=['get'], detail=False, url_path='test')
    def test(self, request):
        try:
            from functools import reduce
            from api_key.models import APIKey
            points =0
            employee_id = request.GET.get('employee_id', None)
            if not  employee_id:
                return Response({'error': "user not found"}, status=400)
            engineer = User.objects.get(employee_id=employee_id)
            tests = Test.objects.filter(engineer=engineer,created__lte='2023-06-30',
                    created__gte='2023-01-01').distinct()

            online_type_of_test = Question.objects.filter(title='Select type of test', form_name='online_test')
            offline_type_of_test = Question.objects.filter(title='Select type of test', form_name='offline_test')
            online_test_id = Answer.objects.filter(object_id__in=tests.filter().values_list('id', flat=True), content_type__model='test', question=online_type_of_test[0]).values_list('object_id', flat=True)
            offline_test_id = Answer.objects.filter(object_id__in=tests.filter().values_list('id', flat=True), content_type__model='test', question=offline_type_of_test[0]).values_list('object_id', flat=True)
            passed_online_test = Test.objects.filter(id__in=online_test_id, status='passed')
            passed_offline_test = Test.objects.filter(id__in=offline_test_id, status='passed')
            failed_online_test = Test.objects.filter(id__in=online_test_id, status='failed')
            failed_offline_test = Test.objects.filter(id__in=offline_test_id, status='failed')
            feedback_due_online_test = Test.objects.filter(id__in=online_test_id, status='feedback_due')
            feedback_due_offline_test = Test.objects.filter(id__in=offline_test_id, status='feedback_due')
            MCQ_question = Question.objects.get(title='Number of MCQ questions')
            MCQ_question_answer = Answer.objects.filter(
                object_id__in=tests.filter().values_list('id', flat=True),
                content_type__model='test', question=MCQ_question
            ).values_list('answer', flat=True)
            total_mcqs = reduce(lambda x, y: int(x) + int(y), MCQ_question_answer) if MCQ_question_answer else 0
            coding_question = Question.objects.get(title='Number of coding questions')
            coding_question_answer = Answer.objects.filter(
                object_id__in=tests.filter().values_list('id', flat=True),
                content_type__model='test', question=coding_question
            ).values_list('answer', flat=True)
            total_coding = reduce(lambda x, y: int(x) + int(y), coding_question_answer) if coding_question_answer else 0
            for test in tests:
                platform_name = None
                mcqs, coding_answers = 0, 0
                online_test = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                    question__title='Select type of test',
                                                    question__form_name='online_test').first()
                if not online_test:
                    test_type = 'offline'
                else:
                    test_type = 'online'
                    platform = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                     question__title='Platform',
                                                     question__form_name='online_test').first()
                    if platform:
                        platform_name = platform.answer
                MCQ_question_answer = Answer.objects.filter(
                    object_id=test.id, content_type__model='test', question__title='Number of MCQ questions'
                ).first()
                if MCQ_question_answer:
                    mcqs = MCQ_question_answer.answer

                coding_question_answer = Answer.objects.filter(
                    object_id=test.id, content_type__model='test', question__title='Number of coding questions'
                ).first()
                if coding_question_answer:
                    coding_answers = coding_question_answer.answer

                employee_associated = test.engineer.all()
                points = points + self.calculate_points(
                    test_type=test_type,
                    test_current_status=test.status,
                    test_platform_name=platform_name,
                    no_mcq_q=mcqs, no_coding_q=coding_answers,
                    no_of_people_involved=len(employee_associated)
                )

            data = {
                "Name": engineer.employee_name,
                "Total Test": tests.count(),
                "Total point": round(points, 2),
                "Total MCQ questions": total_mcqs,
                "Total Coding Questions": total_coding,
                "Offline Test": len(offline_test_id),
                "Total Offline Test Passed": passed_offline_test.count(),
                "Total Offline Test Failed": failed_offline_test.count(),
                "Online Test": len(online_test_id),
                "Total  Online Passed Test": passed_online_test.count(),
                "Total Online Test Failed": failed_online_test.count(),
                "Total FeedbackDue Online Test": feedback_due_online_test.count(),
                "Total FeedbackDue Offline Test": feedback_due_offline_test.count(),
            }
            return Response({"message": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @staticmethod
    def calculate_mcq_points(no_of_mcq):
        first_twenty_points = (20 if no_of_mcq > 20 else no_of_mcq) * 0.25
        next_ten_points = (10 if no_of_mcq > 30 else no_of_mcq - 20) * 0.20
        rest_all_points = (no_of_mcq - 30 if no_of_mcq > 30 else -1) * 0.15
        points = first_twenty_points + (next_ten_points if next_ten_points > 0 else 0) + (
            rest_all_points if rest_all_points > 0 else 0)
        return round(points, 2)

    def calculate_points(self, test_platform_name, test_type, test_current_status,
                         no_of_people_involved=0, no_mcq_q=0, no_coding_q=0):
        points = 0
        if test_type.lower() == 'online':
            if no_mcq_q and no_coding_q:
                test_points = self.calculate_mcq_points(int(no_mcq_q)) + int(no_coding_q) * 3
                bonus_points = 0.75 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            elif no_coding_q:
                test_points = int(no_coding_q) * 3
                bonus_points = 1 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            elif no_mcq_q:
                test_points = self.calculate_mcq_points(int(no_mcq_q))
                bonus_points = 0.5 * (1 if test_current_status == 'passed' else 0)
                points = (test_points + bonus_points) / no_of_people_involved
            else:
                pass
        elif test_type.lower() == 'offline':
            test_points = 5
            bonus_points = 2 * (1 if test_current_status == 'passed' else 0)
            points = (test_points + bonus_points) / no_of_people_involved
        else:
            pass
        return round(points, 2)

    @action(methods=['get'], detail=False, url_path='all')
    def get_all(self, request, *args, **kwargs):
        try:
            from api_key.models import APIKey
            employee_info = {}
            tests = Test.objects.filter(created__lte='2023-06-30',created__gte='2023-01-01').distinct()
            for test in tests:
                platform_name = None
                mcqs, coding_answers = 0, 0
                online_test = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                    question__title='Select type of test',
                                                    question__form_name='online_test').first()
                if not online_test:
                    test_type = 'offline'
                else:
                    test_type = 'online'
                    platform = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                                     question__title='Platform',
                                                     question__form_name='online_test').first()
                    if platform:
                        platform_name = platform.answer
                MCQ_question_answer = Answer.objects.filter(
                    object_id=test.id, content_type__model='test', question__title='Number of MCQ questions'
                ).first()
                if MCQ_question_answer:
                    mcqs = MCQ_question_answer.answer

                coding_question_answer = Answer.objects.filter(
                    object_id=test.id, content_type__model='test', question__title='Number of coding questions'
                ).first()
                if coding_question_answer:
                    coding_answers = coding_question_answer.answer

                employee_associated = test.engineer.all()
                points = self.calculate_points(
                    test_type=test_type,
                    test_current_status=test.status,
                    test_platform_name=platform_name,
                    no_mcq_q=mcqs, no_coding_q=coding_answers,
                    no_of_people_involved=len(employee_associated)
                )

                for employee in employee_associated:
                    employee_data = employee_info.get(employee.employee_id, None)
                    if employee_data:
                        employee_data['total_points'] = round(employee_data['total_points'] + points, 1)
                        employee_data['no_of_test_given'] = employee_data['no_of_test_given'] + 1
                    else:
                        employee_info[employee.employee_id] = {
                            "name": employee.employee_name,
                            "total_points": points,
                            "no_of_test_given": 1
                        }
            if request.GET.get('export', None):
                import csv
                file = open("employee_info.csv", 'w')
                writer = csv.writer(file)
                writer.writerow(['Employee Id', 'Employee Name', 'Total Test', 'Total Points'])
                for emp_id in employee_info.keys():
                    writer.writerow([emp_id, employee_info[emp_id]['name'], employee_info[emp_id]['no_of_test_given'], employee_info[emp_id]['total_points']])
                file.flush()
            return Response({"data": employee_info}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)
