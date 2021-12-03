import csv
import json
from operator import or_
from functools import reduce
from datetime import datetime
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Subquery, OuterRef

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin

from api_key.models import APIKey
from consultant.serializers import *
from employee.models import tag_users
from project.utils import fetch_scrum_masters
from attachment.serializers import AttachmentSerializer
from activity.serializers import Activity, ActivitySerializer
from notification.utils import create_notification, push_notification
from project.models import ProjectStatus, ConsultantFeedback, FEEDBACK_CHOICES
from log1.utils import get_page_limits, write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG
from consultant.utils import close_marketing, start_marketing, send_exit_process_mail, send_exit_interview_detail, \
    terminate_consultant, create_consultant, create_activity, send_notification_for_user, marketing_days_filter, \
    candidate_filter, pre_joining_feedback_notification, engineering_feedback_notification


# Route - /v2/consultant/
class ConsultantV2ViewSets(viewsets.ModelViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            first, last = get_page_limits(request)
            sort_by = request.GET.get('sort_by', None)

            consultants, sub_data = candidate_filter(request)
            if sub_data == 'error':
                write_info(message=consultants, function='ConsultantV2ViewSets_list', request=request)
                return Response({"message": ERROR_MSG, "error": consultants}, status=400)

            status_obj = sub_data["status_obj"]
            count = {
                "total": consultants.count(),
                "offer": status_obj['offer'].count(),
                "sub_status": sub_data["sub_status_obj"],
                "on_bench": status_obj['on_bench'].count(),
                "on_project": status_obj['on_project'].count(),
                "terminated": status_obj['terminated'].count(),
                "marketing_candidate": status_obj['marketing_candidate'].count(),
            }

            if sort_by in ['name', 'created']:
                consultants = consultants.order_by(sort_by)

            serializer = ConsultantV2ListSerializer(consultants[first:last], many=True)
            return Response({"count": count, "data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='filters')
    def filters(self, request):
        try:
            filters = {
                "on_project": [],
                "marketing_candidate": [],
                "on_bench": [
                    {"display_name": "Bench", "name": "non_pool"},
                    {"display_name": "In Pool", "name": "in_pool"},
                ],
                "offer": [
                    {"display_name": "In Offer", "name": "in_offer"},
                    {"display_name": "On-boarded", "name": "on_boarded"},
                ],
                "terminated": [
                    {"display_name": "Fired", "name": "fired"},
                    {"display_name": "Resigned", "name": "resigned"},
                    {"display_name": "Absconded", "name": "absconded"},
                ]
            }
            return Response({"data": filters}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='export')
    def export(self, request):
        try:
            consultants, error = candidate_filter(request)
            if error == 'error':
                write_info(message=error, function='ConsultantV2ViewSets_list', request=request)
                return Response({"message": ERROR_MSG, "error": consultants}, status=400)

            response = HttpResponse(content_type='text/csv')
            writer = csv.writer(response)
            writer.writerow(['Name', 'Email', 'Phone Number'])
            response['Content-Disposition'] = "attachment; filename=Consultants.csv"
            for consultant in consultants:
                writer.writerow([consultant.name, consultant.email, consultant.phone_no])

            return response
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant/
class ConsultantViewSets(viewsets.ModelViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_submission_data(queryset, filter_by_status, first, last):
        try:
            data_counts = {
                'total': queryset.count(),
                'sub': queryset.filter(status='sub').count(),
                'project': queryset.filter(status='project').count(),
                'interview': queryset.filter(status='interview').count()
            }

            if filter_by_status:
                queryset = queryset.filter(status=filter_by_status)

            data = queryset[first:last].annotate(
                city=F('lead__city'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('created_by__employee_name'),
                consultant_name=F('consultant_marketing__consultant__name'),
            ).values('id', 'rate', 'consultant_name', 'company_name', 'marketer_name', 'city', 'project', 'client')

            return data, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    @staticmethod
    def get_interview_data(queryset, filter_by_status, first, last):
        try:
            # Interview counts by status
            queryset = queryset.order_by('-modified').distinct('modified')

            data_counts = {
                'total': queryset.count(),
                'offer': queryset.filter(status='offer').count(),
                'failed': queryset.filter(status='failed').count(),
                'scheduled': queryset.filter(status='scheduled').count(),
                'cancelled': queryset.filter(status='cancelled').count(),
                'rescheduled': queryset.filter(status='rescheduled').count(),
                'feedback_due': queryset.filter(status='feedback_due').count(),
            }

            if filter_by_status:
                queryset = queryset.filter(status=filter_by_status)

            data = queryset[first:last].annotate(
                client=F('submission__client'),
                project=F('submission__project'),
                ctb=F('supervisor__employee_name'),
                job_title=F('submission__lead__job_title'),
                marketer_name=F('submission__created_by__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'round', 'status', 'start_time', 'end_time', 'interview_mode', 'submission_id', 'status',
                     'ctb', 'marketer_name', 'consultant_name', 'client', 'company_name', 'project', 'job_title',
                     'modified', 'created')

            return data, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    @staticmethod
    def get_project_data(queryset, filter_by_status):
        try:
            # count of project by status
            data_counts = {
                'total': queryset.count(),
                'new': queryset.filter(statuses__status='new', statuses__is_current=True).count(),
                'joined': queryset.filter(statuses__status='joined', statuses__is_current=True).count(),
                'received': queryset.filter(statuses__status='received', statuses__is_current=True).count(),
                'on_boarded': queryset.filter(statuses__status='on_boarded', statuses__is_current=True).count(),
                'not_joined': queryset.filter(statuses__status='not_joined', statuses__is_current=True).count(),
            }

            queryset = queryset.order_by('-start_date')
            if filter_by_status:
                queryset = queryset.filter(statuses__status=filter_by_status, statuses__is_current=True)

            project_status = ProjectStatus.objects.filter(
                project=OuterRef("pk"), is_current=True)

            data = queryset.annotate(
                client=F('submission__client'),
                consultant_name=F('consultant__name'),
                job_title=F('submission__lead__job_title'),
                status=Subquery(project_status.values('status')[:1]),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'consultant_name', 'city', 'company_name', 'client', 'rate', 'marketer_name', 'created',
                     'status', 'employer', 'start_date', 'end_date', 'job_title')
            return data, data_counts
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    def list(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            query = request.GET.get('query', None)
            consultants = Consultant.objects.all()
            roles = request.user.roles

            if 'admin' in roles or 'proxy' in roles:
                consultants = consultants.filter(
                    Q(marketing__teams=request.user.team, marketing__in_pool=False, marketing__status='open') |
                    Q(marketing__marketer=request.user, marketing__status='open') |
                    Q(marketing__in_pool=True, marketing__status='open') |
                    Q(pocs__poc=request.user)
                )

            elif 'marketer' in request.user.roles:
                recruits = Consultant.objects.none()
                if 'recruiter' in roles:
                    recruits = consultants.filter(pocs__poc=request.user)
                consultants = consultants.filter(
                    Q(marketing__marketer=request.user) |
                    Q(marketing__primary_marketer=request.user) |
                    Q(marketing__in_pool=True, marketing__status='open')
                )
                consultants = (consultants | recruits).distinct()

            if 'recruiter' in roles:
                recruits = consultants.filter(pocs__poc=request.user)
                consultants = (consultants | recruits).distinct()

            if query:
                consultants = consultants.filter(name__istartswith=query.lstrip().replace(':amp:', '&'))
            else:
                consultants = consultants.filter(marketing__status='open').exclude(
                    status='terminated')

            consultants = consultants.order_by('id').distinct('id')[:100]
            serializer = ConsultantListSerializer(consultants, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            consultant_id = kwargs.get('pk')
            submission = request.GET.get('submission', 'false')
            if submission.lower() == "true":
                consultant = get_object_or_404(Consultant, id=consultant_id)
                serializer = ConsultantSubmissionSerializer(consultant)
            else:
                consultant = get_object_or_404(Consultant, id=consultant_id)
                serializer = self.serializer_class(consultant)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        data = request.data
        consultant = Consultant.objects.filter(email__iexact=data['email'])
        if consultant:
            return Response({"message": "Consultant Already Exist"}, status=400)
        try:
            consultant = Consultant.objects.create(
                ssn=data['ssn'],
                name=data['name'],
                email=data['email'],
                is_w2=data['is_w2'],
                skills=data['skills'],
                gender=data['gender'],
                phone_no=data['phone_no'],
                current_city=data['current_city'],
                date_of_birth=data['date_of_birth'],
                skype=request.data.get('skype', None),
                links=request.data.get('links', None),
                work_type=request.data.get('work_type', 'full_time'),
            )

            # Creating Consultant Original Profile Consultant
            ConsultantProfile.objects.create(
                title="Original",
                consultant=consultant,
                visa_end=data['visa_end'],
                profile_owner=request.user,
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
                current_city=data['current_city'],
                date_of_birth=data['date_of_birth'],
                links=request.data.get('links', None),
            )

            # Creating Recruiter of Consultant
            ConsultantPOC.objects.create(
                poc_id=data['recruiter'],
                consultant=consultant,
                poc_type='recruiter',
                start=timezone.now(),
            )

            # Creating Retention of Consultant
            if request.data.get('retention', None):
                ConsultantPOC.objects.create(
                    poc_id=data['retention'],
                    consultant=consultant,
                    poc_type='retention',
                    start=timezone.now(),
                )

            # Creating Work-Auth
            WorkAuth.objects.create(
                is_current=True,
                consultant=consultant,
                visa_end=data['visa_end'],
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
            )
            # Create Employer
            PayrollEmployer.objects.create(
                consultant=consultant,
                name=data['payroll_employer'],
                start=data['employer_start_date'],
            )

            desc = f"{request.user.employee_name} added consultant manually"
            create_activity(consultant.id, 'consultant', request.user, desc, 'created')

            return Response({"data": ConsultantSerializer(consultant).data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk'))
            serializer = ConsultantUpdateSerializer(consultant, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            important_fields = {
                "ssn": "SSN",
                "is_w2": "W2",
                "name": "Name",
                "email": "Email",
                "links": "Links",
                "skills": "Skills",
                "gender": "Gender",
                "skype": "Skype Id",
                "phone_no": "Phone No",
                "current_city": "Current City",
                "date_of_birth": "Date of Birth",
            }
            changed_fields = []
            for field in request.data.keys():
                if getattr(consultant, field) != request.data[field]:
                    changed_fields.append(important_fields[field])

            serializer.save()
            profiles = consultant.profiles.filter(title__iexact='Original')
            if profiles:
                profile = profiles.first()
                profile.links = consultant.links
                profile.current_city = consultant.current_city
                profile.date_of_birth = consultant.date_of_birth
                profile.save()

            # Push Notification
            title = f"{consultant.name}'s details updated by {request.user.employee_name}"
            send_notification_for_user(consultant, request.user, title, 'consultant')

            # Activity
            if changed_fields:
                desc = f"{request.user.employee_name} updated following fields: {', '.join(changed_fields)}"
                create_activity(consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Consultant Updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Method DELETE not allowed."}, status=405)

    @action(methods=['get'], detail=True, url_path='activities')
    def activities(self, request, pk):
        try:
            activities = Activity.objects.filter(
                object_id=pk, content_type__model='consultant'
            ).order_by('created')
            serializer = ActivitySerializer(activities, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='set_password')
    def set_consultant_password(self, request):
        try:
            if request.user.is_superuser:
                consultant = get_object_or_404(Consultant, id=request.data['consultant_id'])
                consultant.set_password(request.data['new_password'])
                consultant.save()
                return Response({'message': 'Password Changed Successfully'}, status=200)
            else:
                return Response({'message': DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='search')
    def search(self, request):
        try:
            query = request.GET.get('query', None)
            if query:
                consultants = Consultant.objects.filter(
                    name__istartswith=query.lstrip().replace(':amp:', '&')
                ).order_by('name')
            else:
                consultants = Consultant.objects.all().order_by('name')
            data = consultants[:10].values('id', 'name', 'email')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post', 'put'], detail=True, url_path='education')
    def education(self, request, pk):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)

        if request.method == 'POST':
            try:
                data = request.data
                education = Education.objects.create(
                    consultant_id=pk,
                    city=data['city'],
                    major=data['major'],
                    remark=data['remark'],
                    org_name=data['org_name'],
                    edu_type=data['edu_type'],
                    end_date=data['end_date'],
                )
                serializer = EducationSerializer(education)

                # Push Notification
                title = f"{education.consultant.name}'s education added by {request.user.employee_name}"
                send_notification_for_user(education.consultant, request.user, title, 'education', education.id)

                # Activity
                desc = f"{request.user.employee_name} added Education details"
                create_activity(education.consultant.id, 'consultant', request.user, desc, 'created')
                return Response({"data": serializer.data, "message": "Education details added"}, status=201)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        else:
            try:
                education = get_object_or_404(Education, id=pk)
                serializer = EducationSerializer(education, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                # Push Notification
                title = f"{education.consultant.name}'s education details updated by {request.user.employee_name}"
                send_notification_for_user(education.consultant, request.user, title, 'education', education.id)

                # Activity
                desc = f"{request.user.employee_name} updated Education details"
                create_activity(education.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Education details updated"}, status=202)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post', 'put'], detail=True, url_path='experience')
    def experience(self, request, pk):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)

        if request.method == 'POST':
            try:
                data = request.data
                experience = Experience.objects.create(
                    consultant_id=pk,
                    city=data['city'],
                    title=data['title'],
                    remark=data['remark'],
                    company=data['company'],
                    exp_type=data['exp_type'],
                    end_date=data['end_date'],
                    start_date=data['start_date'],
                )
                serializer = ExperienceSerializer(experience)

                # Push Notification
                title = f"{experience.consultant.name}'s experience added by {request.user.employee_name}"
                send_notification_for_user(experience.consultant, request.user, title, 'experience', experience.id)

                # Activity
                desc = f"{request.user.employee_name} added Experience details"
                create_activity(experience.consultant.id, 'consultant', request.user, desc, 'created')
                return Response({"data": serializer.data, "message": "Experience details added"}, status=201)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        else:
            try:
                experience = get_object_or_404(Experience, id=pk)
                serializer = ExperienceSerializer(experience, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                # Push Notification
                title = f"{experience.consultant.name}'s experience details updated by {request.user.employee_name}"
                send_notification_for_user(experience.consultant, request.user, title, 'experience', experience.id)

                # Activity
                desc = f"{request.user.employee_name} updated Experience details"
                create_activity(experience.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Experience details updated"}, status=202)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='marketing')
    def marketing(self, request, pk):
        first, last = get_page_limits(request)
        marketing_stage = request.GET.get('stage')
        filter_by_status = request.GET.get("filter_by_status", None)

        try:
            if marketing_stage == 'interview':
                interviews = Interview.objects.filter(
                    submission__consultant_marketing__end=None,
                    submission__consultant_marketing__status='open',
                    submission__consultant_marketing__consultant_id=pk,
                )
                data, counts = self.get_interview_data(interviews, filter_by_status, first, last)
                if counts == "error":
                    return Response({"error": str(data)}, status=400)
            else:
                projects = Project.objects.filter(
                    Q(consultant_id=pk) |
                    Q(submission__consultant_marketing__consultant_id=pk)
                )
                data, counts = self.get_project_data(projects, filter_by_status)
                if counts == "error":
                    return Response({"error": str(data)}, status=400)
            return Response({"data": data, "total": counts}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='documents')
    def documents(self, request, pk):
        try:
            consultant = get_object_or_404(Consultant, id=pk)
            queryset = consultant.attachments.all()
            serializer = AttachmentSerializer(queryset, many=True)
            return Response({'data': serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get', 'post', 'put'], detail=True, url_path='payroll_employer')
    def payroll_employer(self, request, pk):
        if request.method == 'GET':
            try:
                consultant = get_object_or_404(Consultant, id=pk)
                serializer = PayrollEmployerSerializer(consultant.employers.all().order_by('-start'), many=True)
                return Response({"data": serializer.data}, status=200)
            except Exception as error:
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        elif request.method == 'PUT':
            try:
                employer = PayrollEmployer.objects.get(id=pk)
                prev_start = employer.start
                serializer = PayrollEmployerSerializer(employer, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                # Push Notification
                title = f"{employer.consultant.name}'s employer updated by {request.user.employee_name}"
                send_notification_for_user(employer.consultant, request.user, title, 'payrollemployer')

                # Activity
                desc = f"{request.user.employee_name} updated Employer start date from {prev_start} to {employer.start}"
                create_activity(employer.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Employer updated"}, status=202)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        else:
            try:
                consultant = get_object_or_404(Consultant, id=pk)
                serializer = PayrollEmployerSerializer(data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save(consultant=consultant)

                # Push Notification
                title = f"{consultant.name}'s employer added by {request.user.employee_name}"
                send_notification_for_user(consultant, request.user, title, 'payrollemployer')

                # Activity
                desc = f"{request.user.employee_name} added employer - {serializer.data['name']}"
                create_activity(consultant.id, 'consultant', request.user, desc, 'created')
                return Response({"data": serializer.data, "message": "Employer added"}, status=201)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get', 'post'], detail=True, url_path='rate_revision')
    def rate_revision(self, request, pk):
        if request.method == 'GET':
            try:
                rate_revision = ConsultantRateRevision.objects.filter(consultant=pk).order_by('-id')
                data = rate_revision.values('id', 'rate', 'start', 'end', 'previous_rate', 'feedback', 'consultant')
                return Response({"data": data}, status=200)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        else:
            try:
                qs = ConsultantRateRevision.objects.filter(
                    consultant_id=request.data['consultant'], end=None
                )
                prev_rate = 0
                if qs:
                    prev_rate_obj = qs.first()
                    prev_rate = prev_rate_obj.rate
                    prev_rate_obj.end = datetime.today()
                    prev_rate_obj.save()

                rate_obj = ConsultantRateRevision.objects.create(
                    previous_rate=prev_rate,
                    rate=request.data['rate'],
                    start=request.data['start'],
                    feedback=request.data['feedback'],
                    consultant_id=request.data['consultant']
                )
                serializer = ConsultantRateRevisionSerializer(rate_obj)

                # Push Notification
                title = f"{rate_obj.consultant.name}'s rate revised to {rate_obj.rate} by {request.user.employee_name}"
                send_notification_for_user(rate_obj.consultant, request.user, title, 'consultantraterevision')

                # Activity
                desc = f"{request.user.employee_name.title()} revised rate from {prev_rate} to {rate_obj.rate}"
                create_activity(rate_obj.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Rate revised"}, status=201)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='margin')
    def margin(self, request, pk):
        try:
            projects = Project.objects.filter(
                Q(consultant_id=pk) |
                Q(submission__consultant_marketing__consultant_id=pk)
            )
            project_data = []
            margin, margin_percentage = 0, 0
            if projects.count() == 1:
                project_rate = projects.first().rate
                rate_revision = ConsultantRateRevision.objects.filter(consultant=pk, end=None)
                if rate_revision:
                    consultant_rate = rate_revision.first().rate
                    margin = project_rate - consultant_rate
                    margin_percentage = (margin / project_rate) * 100

            for project in projects:
                project_data.append(
                    {
                        "rate": project.rate,
                        "client": project.submission.client,
                    }
                )
            data = {
                "margin": margin,
                "projects": project_data,
                "margin_percentage": margin_percentage,
                "lock_flag": True if margin_percentage < 21 else False,
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant_bench/
class ConsultantBenchViewSets(ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        visa = request.GET.get('visa', [])
        days = request.GET.get('days', None)
        query = request.GET.get('query', None)
        skills = request.GET.get('skills', [])
        gender = request.GET.get('gender', None)
        team_name = request.GET.get('team', None)
        con_status = request.GET.get('status', 'all')

        try:
            # Consultants search based on name, email, recruiter and location
            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = Consultant.objects.filter(
                    Q(email__iexact=query) |
                    Q(name__icontains=query) |
                    Q(skills__istartswith=query) |
                    Q(current_city__istartswith=query) |
                    Q(pocs__poc__employee_name__istartswith=query, pocs__end=None)
                )
            else:
                consultants = Consultant.objects.exclude(status='terminated')

            # Team wise Filter
            if team_name and team_name != 'all' and team_name.lower() != 'consultadd':
                consultants = consultants.filter(marketing__teams__name=team_name, marketing__status='open')

            if gender:
                consultants = consultants.filter(gender=gender)

            if days:
                day_filter = marketing_days_filter(days)
                consultants = consultants.filter(**day_filter)

            if type(skills) is not list:
                skills = json.loads(skills)
            if type(visa) is not list:
                visa = json.loads(visa)

            if len(skills) > 0:
                consultants = consultants.filter(reduce(or_, [Q(skills__icontains=q) for q in skills]))

            if len(visa) > 0:
                consultants = consultants.filter(work_auth__visa_type__in=visa, work_auth__is_current=True)

            consultants = consultants.order_by('id').distinct('id')

            open_candidates = list(ConsultantMarketing.objects.filter(
                status='open'
            ).order_by('consultant_id').distinct('consultant_id').values_list('consultant_id', flat=True))

            offer_candidates = list(consultants.filter(
                projects__statuses__status__in=['new', 'received', 'on_boarded'],
                projects__statuses__is_current=True).order_by('id').distinct('id').values_list(
                'id', flat=True))

            obj = {
                "all": consultants.all(),
                "on_project": consultants.filter(
                    projects__statuses__status='joined', projects__statuses__is_current=True),
                "in_offer": consultants.filter(
                    projects__statuses__status__in=['new', 'received'], projects__statuses__is_current=True),
                "on_boarded": consultants.filter(
                    projects__statuses__status='on_boarded', projects__statuses__is_current=True),
                "candidate": consultants.filter(
                    status='on_bench').exclude(id__in=open_candidates),
                "in_pool": consultants.filter(
                    marketing__status='open', marketing__in_pool=True).exclude(id__in=offer_candidates),
                "in_marketing": consultants.filter(
                    marketing__status='open', marketing__in_pool=False).exclude(id__in=offer_candidates)
            }

            count = {
                "total": obj['all'].count(),
                "in_pool": obj['in_pool'].count(),
                "in_offer": obj['in_offer'].count(),
                "on_project": obj['on_project'].count(),
                "on_boarded": obj['on_boarded'].count(),
                "in_marketing": obj['in_marketing'].count(),
                "candidate": obj['candidate'].count() if obj['candidate'].count() > 0 else 0
            }

            # Filter Consultant by status and In pool
            if con_status:
                consultants = obj[con_status]

            poc = ConsultantPOC.objects.filter(
                consultant=OuterRef("pk"), end=None, poc_type='recruiter')

            rate = ConsultantRateRevision.objects.filter(
                consultant=OuterRef("pk"), end=None)

            marketing = ConsultantMarketing.objects.filter(
                consultant=OuterRef("pk"), status='open')

            work_auth = WorkAuth.objects.filter(
                consultant=OuterRef("pk"), is_current=True
            )

            data = consultants[first:last].annotate(
                rate=Subquery(rate.values('rate')[:1]),
                rtg=Subquery(marketing.values('rtg')[:1]),
                visa=Subquery(work_auth.values('visa_type')[:1]),
                in_pool=Subquery(marketing.values('in_pool')[:1]),
                marketing_start=Subquery(marketing.values('start')[:1]),
                recruiter=Subquery(poc.values('poc__employee_name')[:1]),
                preferred_location=Subquery(marketing.values('preferred_location')[:1]),
                previous_marketing_days=Subquery(marketing.values('previous_marketing_days')[:1]),
            ).values('id', 'name', 'skills', 'preferred_location', 'recruiter', 'rtg', 'rate', 'in_pool',
                     'marketing_start', 'previous_marketing_days', 'visa')
            return Response({"data": data, "count": count}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant_marketing/
class ConsultantMarketingViewSets(CreateModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantMarketing.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantMarketingCycleSerializer

    def list(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            marketing = ConsultantMarketing.objects.filter(
                consultant_id=request.GET.get('consultant')
            )
            serializer = self.serializer_class(marketing, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            qs = Consultant.objects.filter(id=request.data['consultant'])
            if not qs:
                return Response({"message": "Consultant not found"}, status=404)
            open_consultant = qs.filter(marketing__status='open')
            if open_consultant:
                return Response({"message": "Marketing is already started"}, status=400)

            consultant = qs.first()
            queryset = consultant.marketing.filter(status='close')

            fut_marketing = consultant.marketing.filter(start__gt=datetime.today())
            if fut_marketing:
                future_date = fut_marketing.first().start
                return Response({"message": f"Marketing will start on {str(future_date)}"}, status=400)

            if queryset:
                latest_marketing_cycle = queryset.latest('end')
            else:
                latest_marketing_cycle = None

            if consultant.status == 'terminated':
                consultant.status = 'on_bench'
                consultant.save()

            reset_days = request.data.get('reset_days', 'true')
            if reset_days or reset_days == 'true':
                previous_marketing_days = 0
            else:
                if not latest_marketing_cycle:
                    previous_marketing_days = 0
                else:
                    previous_marketing_days = 0
                    if latest_marketing_cycle.end and latest_marketing_cycle.start:
                        previous_marketing_days = (latest_marketing_cycle.end - latest_marketing_cycle.start).days

            cycle = 1
            if latest_marketing_cycle:
                cycle = latest_marketing_cycle.cycle + 1

            consultant_marketing = ConsultantMarketing.objects.create(
                cycle=cycle,
                status='close',
                rtg=request.data.get('rtg', False),
                in_pool=request.data.get('in_pool'),
                start=request.data.get('marketing_start'),
                consultant_id=request.data.get('consultant'),
                previous_marketing_days=previous_marketing_days,
                preferred_location=request.data.get('preferred_location'),
            )
            primary_marketer = request.data.get('primary_marketer', None)
            if primary_marketer:
                consultant_marketing.primary_marketer_id = primary_marketer
                consultant_marketing.save()

            teams = request.data.get('teams', [])
            for team in teams:
                consultant_marketing.teams.add(get_object_or_404(Team, name=team))

            marketer_ids = request.data.get('marketers', [])
            for marketer_id in marketer_ids:
                marketer = get_object_or_404(User, id=marketer_id)
                consultant_marketing.marketer.add(marketer)
            start_marketing()

            # Activity
            desc = f"{request.user.employee_name} started Marketing from {consultant_marketing.start}"
            create_activity(consultant.id, 'consultant', request.user, desc, 'created')
            return Response({"message": "Marketing started"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            consultant_marketing = get_object_or_404(ConsultantMarketing, id=kwargs.get('pk'))
            serializer = ConsultantMarketingCreateSerializer(consultant_marketing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Push Notification
            title = f"{consultant_marketing.consultant.name}'s marketing detail updated by {request.user.employee_name}"
            send_notification_for_user(consultant_marketing.consultant, request.user, title, 'consultantmarketing')

            # Activity
            desc = f"{request.user.employee_name} updated marketing details"
            create_activity(consultant_marketing.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Marketing cycle updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['put'], detail=True, url_path='stop_marketing')
    def stop_marketing(self, request, pk):
        try:
            marketing = get_object_or_404(ConsultantMarketing, id=pk)
            marketing.end = request.data.get('end')
            marketing.save()
            close_marketing()

            # Activity
            desc = f"{request.user.employee_name} stopped marketing from {str(marketing.end)}"
            create_activity(marketing.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"message": "Marketing cycle stopped"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='remarketing')
    def remarketing(self, request):
        try:
            marketing = ConsultantMarketing.objects.filter(
                consultant_id=request.GET.get('consultant')
            )
            serializer = self.serializer_class(marketing, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='previous_marketing')
    def previous_marketing(self, request):
        try:
            qs = ConsultantMarketing.objects.filter(consultant_id=request.GET.get('consultant'))
            if qs:
                data = self.serializer_class(qs.latest('end')).data
            else:
                data = []
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Marketer assignment
    @action(methods=["put"], detail=True, url_path='marketer_assignment')
    def marketer_assignment(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"message": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.teams.all()):
                marketer_ids = request.data.get('marketers', None)
                marketers_name = []
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.add(marketer)
                    marketers_name.append(marketer.employee_name)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)

                if len(marketers_name) > 1:
                    marketer_str = "marketers"
                else:
                    marketer_str = "marketer"

                # Push Notification
                title = f"{request.user.employee_name} assigned following {marketer_str} - {', '.join(marketers_name)}"
                send_notification_for_user(consultant_marketing.consultant, request.user, title, 'consultantmarketing')

                # Activity
                create_activity(consultant_marketing.consultant.id, 'consultant', request.user, title, 'updated')
                return Response({"data": serializer.data, "message": "marketers assigned"}, status=202)
            else:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Team Assignment
    @action(methods=['put'], detail=True, url_path='team_assignment')
    def team_assignment(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"message": "Consultant is not in Marketing"})
            if 'superadmin' in request.user.roles:
                team_ids = request.data.get('teams')
                for team_id in team_ids:
                    team = get_object_or_404(Team, id=team_id)
                    consultant_marketing.teams.add(team)
                serializer = TeamSerializer(consultant_marketing.teams.all(), many=True)
                teams_string = ", ".join(team.name for team in consultant_marketing.teams.all())

                # Push Notification
                title = f"{consultant_marketing.consultant.name} is assigned to team - {teams_string}"
                send_notification_for_user(consultant_marketing.consultant, request.user, title, 'consultantmarketing')

                # Activity
                desc = f"{request.user.employee_name} is assigned to team - {teams_string}"
                create_activity(consultant_marketing.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Team added"}, status=202)
            else:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Remove assigned Marketer from Consultant
    @action(methods=['put'], detail=True, url_path='remove_marketer')
    def remove_marketer(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"message": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.teams.all()):
                marketers_name = []
                marketer_ids = request.data.get('marketers', None)
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.remove(marketer)
                    marketers_name.append(marketer.employee_name)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)

                # Push Notification
                name = consultant_marketing.consultant.name
                title = f"{', '.join(marketers_name)} is unassigned from {name}'s marketing"
                send_notification_for_user(consultant_marketing.consultant, request.user, title, 'consultantmarketing')

                # Activity
                desc = f"{request.user.employee_name} removed following marketers - {', '.join(marketers_name)}"
                create_activity(consultant_marketing.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Marketers removed"}, status=202)
            else:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # Remove team from Consultant
    @action(methods=['put'], detail=True, url_path='remove_team')
    def remove_team(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"message": "Consultant is not in Marketing"})
            if 'superadmin' in request.user.roles:
                team_ids = request.data.get('teams')
                team_string = []
                for team_id in team_ids:
                    team = get_object_or_404(Team, id=team_id)
                    consultant_marketing.teams.remove(team)
                    team_string.append(team.name)
                serializer = TeamSerializer(consultant_marketing.teams.all(), many=True)

                # Push Notification
                title = f"{consultant_marketing.consultant.name} is removed from {team_string}"
                send_notification_for_user(consultant_marketing.consultant, request.user, title, 'consultantmarketing')

                # Activity
                desc = f"{request.user.employee_name} removed from {team_string}"
                create_activity(consultant_marketing.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Team removed"}, status=202)
            else:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant_profile/
class ConsultantProfileViewSets(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantProfile.objects.all()
    serializer_class = ConsultantProfileSerializer
    authentication_classes = (TokenAuthentication,)

    # Return Consultant Profile by ID
    def retrieve(self, request, *args, **kwargs):
        try:
            profile_id = kwargs.get('pk')
            profile = get_object_or_404(ConsultantProfile, id=profile_id)
            serializer = self.serializer_class(profile)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            consultant_id = request.GET.get('con_id', None)
            consultant = get_object_or_404(Consultant, id=consultant_id)
            profiles = consultant.profiles.all()
            serializer = self.serializer_class(profiles, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            suffix = data['title'].strip()
            name = request.user.employee_name
            initials = name.split()[0][0] + name.split()[1][0] if len(name.split()) > 1 else ""
            title = f'{initials.upper()}-{data["visa_type"]}-{data["dob"][:4]}-{suffix}'

            profile = ConsultantProfile.objects.create(
                title=title,
                links=data['links'],
                linkedin=data['linkedin'],
                date_of_birth=data['dob'],
                visa_end=data['visa_end'],
                profile_owner=request.user,
                education=data['education'],
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
                consultant_id=data['consultant'],
                current_city=data['current_city'],
            )
            serializer = self.serializer_class(profile)

            # Push Notification
            title = f"{profile.consultant.name}'s profile created by {request.user.employee_name}"
            send_notification_for_user(profile.consultant, request.user, title, 'consultantprofile')

            # Activity
            desc = f"{request.user.employee_name} created {title} profile"
            create_activity(profile.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Profile created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            profile = get_object_or_404(ConsultantProfile, id=kwargs.get('pk'))
            serializer = self.serializer_class(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                # Push Notification
                title = f"{profile.consultant.name}'s profile updated by {request.user.employee_name}"
                send_notification_for_user(profile.consultant, request.user, title, 'consultantprofile')

                # Activity
                desc = f"{request.user.employee_name} updated {title} profile"
                create_activity(profile.consultant.id, 'consultant', request.user, desc, 'updated')
                return Response({"data": serializer.data, "message": "Profile updated"}, status=202)
            return Response({"message": ERROR_MSG, "error": str(serializer.errors)}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /consultant_poc/
class ConsultantPOCViewSets(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantPOC.objects.all()
    serializer_class = ConsultantPOCSerializer
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            queryset = ConsultantPOC.objects.filter(
                poc_type=request.data['poc_type'], consultant=request.data['consultant'], end=None
            )
            if queryset:
                previous_poc = queryset.first()
                previous_poc.end = date.today()
                previous_poc.save()
            poc = ConsultantPOC.objects.create(
                poc_id=request.data['poc'],
                poc_type=request.data['poc_type'],
                consultant_id=request.data['consultant'],
                start=date.today()
            )

            # Push Notification
            title = f"{poc.poc.employee_name} is added as {poc.poc_type.title()} on {poc.consultant.name}"
            send_notification_for_user(poc.consultant, request.user, title, 'consultant')

            # Activity
            desc = f"{request.user.employee_name} added {poc.poc.employee_name} as {poc.poc_type.title()}"
            create_activity(poc.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"message": "POC added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            instance = get_object_or_404(ConsultantPOC, id=kwargs.get('pk'))
            serializer = self.serializer_class(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Push Notification
            poc_type = instance.poc_type.title()
            poc_name = instance.poc.employee_name
            title = f"{poc_name} is updated as {poc_type} on {instance.consultant.name}"
            send_notification_for_user(instance.consultant, request.user, title, 'consultant')

            # Activity
            desc = f"{request.user.employee_name} updated {poc_name} as {poc_type}"
            create_activity(instance.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "POC updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /consultant_work_auth/
class WorkAuthViewSets(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = WorkAuth.objects.all()
    serializer_class = WorkAuthSerializer
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            instance = WorkAuth.objects.filter(consultant=request.data['consultant'], is_current=True)
            if instance:
                previous_work_auth = instance.first()
                previous_work_auth.is_current = False
                previous_work_auth.save()
            work_auth = WorkAuth.objects.create(
                is_current=True,
                visa_end=request.data['visa_end'],
                visa_type=request.data['visa_type'],
                visa_start=request.data['visa_start'],
                consultant_id=request.data['consultant'],
            )
            profiles = work_auth.consultant.profiles.filter(title__iexact='Original')
            if profiles:
                profile = profiles.first()
                profile.visa_end = work_auth.visa_end
                profile.visa_type = work_auth.visa_type
                profile.visa_start = work_auth.visa_start
                profile.save()

            serializer = self.serializer_class(work_auth)

            # Push Notification
            title = f"{work_auth.consultant.name}'s work authorization is added by {request.user.employee_name}"
            send_notification_for_user(work_auth.consultant, request.user, title, 'workauth')

            # Activity
            desc = f"{request.user.employee_name} added Work Authorization"
            create_activity(work_auth.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Work Auth added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            work_auth = get_object_or_404(WorkAuth, id=kwargs.get('pk'))
            serializer = self.serializer_class(work_auth, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            profiles = ConsultantProfile.objects.filter(
                title__iexact='Original', consultant_id=serializer.data['consultant'])
            if profiles:
                profile = profiles.first()
                profile.visa_start = serializer.data['visa_start']
                profile.visa_end = serializer.data['visa_end']
                profile.visa_type = serializer.data['visa_type']
                profile.save()

            # Push Notification
            title = f"{work_auth.consultant.name}'s work authorization is updated by {request.user.employee_name}"
            send_notification_for_user(work_auth.consultant, request.user, title, 'workauth')

            # Activity
            desc = f"{request.user.employee_name} updated Work Authorization details"
            create_activity(work_auth.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Work Auth added"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /consultant_exit/
class ConsultantExitViewSets(RetrieveModelMixin, ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantExit.objects.all()
    serializer_class = ExitDetailConsultantSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        query = request.GET.get('query', None)
        con_status = request.GET.get('status', 'all')

        try:
            consultants = Consultant.objects.filter(status='terminated')

            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = consultants.filter(
                    Q(email__iexact=query) |
                    Q(name__icontains=query) |
                    Q(skills__istartswith=query)
                )

            total = consultants.all()
            fired = consultants.filter(exit__type='fired').order_by('id').distinct('id')
            resigned = consultants.filter(exit__type='resigned').order_by('id').distinct('id')
            absconded = consultants.filter(exit__type='absconded').order_by('id').distinct('id')

            count = {
                "total": total.count(),
                "fired": fired.count(),
                "resigned": resigned.count(),
                "absconded": absconded.count(),
            }

            if con_status == 'all':
                consultants = consultants.all()
            else:
                consultants = consultants.filter(exit__type=con_status)

            consultants = consultants.order_by('id', '-exit__modified').distinct('id')
            exit_obj = ConsultantExit.objects.filter(consultant=OuterRef("pk"))
            data = consultants[first:last].annotate(
                type=Subquery(exit_obj.values('type')[:1]),
                rehire=Subquery(exit_obj.values('rehire')[:1]),
                last_date=Subquery(exit_obj.values('last_date')[:1]),
                resign_date=Subquery(exit_obj.values('resign_date')[:1]),
            ).values('id', 'name', 'skills', 'type', 'last_date', 'rehire')
            return Response({"data": data, "count": count}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            consultant = get_object_or_404(Consultant, id=request.data.get('consultant'))
            con_exit = ConsultantExit.objects.create(
                status='in_process',
                consultant=consultant,
                created_by=request.user,
                type=request.data.get('type'),
                rehire=request.data.get('rehire', False),
                last_date=request.data.get('last_date', None),
                resign_date=request.data.get('resign_date', None),
                exit_details=request.data.get('exit_details', None),
                legal_status=request.data.get('legal_status', None),
                legal_action=request.data.get('legal_action', False),
                notice_period=request.data.get('notice_period', None),
            )

            reasons = request.data.get('reasons', [])
            for reason in reasons:
                reason = get_object_or_404(ExitReason, id=reason)
                con_exit.reasons.add(reason)

            #  Message for exit interview
            if request.data.get('exit_details', None):
                send_exit_interview_detail(con_exit, request)

            res = "Development Server"
            if request.data.get('last_date', None) and request.data.get('last_date', None) <= str(date.today()):
                terminate_consultant(con_exit, request)
            else:
                # Email for starting Exit Process
                if os.environ.get('ENV', 'local') == 'prod':
                    res, error = send_exit_process_mail(con_exit, 'start', request)
                    if error == 'error':
                        write_exception(res, request)
                        return Response({"message": "Exit process mail not sent", "error": str(res)}, status=400)
            serializer = self.serializer_class(consultant.exit.all().order_by('-created'), many=True)

            # Activity
            desc = f"{request.user.employee_name} started exit process"
            create_activity(consultant.id, 'consultant', request.user, desc, 'updated')
            return Response(
                {"data": serializer.data, "exit_mail": str(res), "message": "Exit process created"}, status=201
            )
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles):
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            con_exit = get_object_or_404(ConsultantExit, id=kwargs.get('pk'))

            #  Message for exit interview
            if request.data.get('exit_details', None) and not con_exit.exit_details:
                send_exit_interview_detail(con_exit, request)

            serializer = ExitConsultantSerializer(con_exit, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if request.data.get('last_date', None) and request.data.get('last_date', None) <= str(date.today()):
                terminate_consultant(con_exit, request)

            # Activity
            desc = f"{request.user.employee_name} updated exit process"
            create_activity(con_exit.consultant.id, 'consultant', request.user, desc, 'updated')

            serializer = self.serializer_class(con_exit)
            return Response({"data": serializer.data, "message": "Exit process updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['put'], detail=True, url_path='cancel')
    def cancel_termination(self, request, pk):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            con_exit = get_object_or_404(ConsultantExit, id=pk)

            if request.data.get('cancel_reason', None) and not con_exit.last_date or con_exit.last_date > date.today():
                con_exit.status = 'cancelled'
                con_exit.cancel_reason = request.data.get('cancel_reason')
                con_exit.save()

                # Email for Exit Process Cancelled
                res = "Development Server"
                if os.environ.get('ENV', 'local') == 'prod':
                    res, error = send_exit_process_mail(con_exit, 'cancel', request)
                    if error == 'error':
                        write_exception(res, request)
                        return Response({"message": "Cancel Termination main not sent", "error": str(res)}, status=400)

                # Activity
                desc = f"{request.user.employee_name} cancelled exit process"
                create_activity(con_exit.consultant.id, 'consultant', request.user, desc, 'updated')

                serializer = self.serializer_class(con_exit)
                return Response(
                    {"data": serializer.data, "exit_mail": str(res), "message": "Exit process cancelled"}, status=202
                )
            return Response({"message": "Exit process can not be cancelled "}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='reason')
    def termination_reason(self, request):
        try:
            reasons = ExitReason.objects.all().values('id', 'name')
            return Response({'data': reasons}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /feedback/
class FeedbackViewSet(GenericViewSet, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin):
    queryset = Feedback.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantFeedbackSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            feedback_type = request.GET.get('type', None)
            feedback = Feedback.objects.filter(consultant_id=kwargs.get('pk')).order_by('-created')
            if feedback_type:
                feedback = feedback.filter(feedback_type=feedback_type)
            serializer = self.serializer_class(feedback, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            feedback = Feedback.objects.create(
                created_by=request.user,
                rating=request.data.get('rating'),
                consultant_id=request.data.get('consultant'),
                feedback_type=request.data.get('feedback_type'),
                feedback_text=request.data.get('feedback_text'),
            )
            user_list = []
            tags = request.data.get('tagged_user', [])
            if len(tags) > 0:
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                tag_data = {
                    "model": "feedback",
                    "object_id": feedback.id,
                    "tags": tags
                }
                tag_users(tag_data)
            employee_name = request.user.employee_name
            consultant = feedback.consultant
            title = f"{employee_name} tagged you in a {consultant.name}'s feedback"
            notification_data = {
                'title': title,
                'category': 'info',
                'description': title,
                'target_id': feedback.id,
                'sender_user_type': 'user',
                'target_type': 'feedback',
                'parent_id': consultant.id,
                'parent_type': 'consultant',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
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
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'sub_target': 'feedback',
                    'target_id': consultant.id,
                    'sub_target_id': feedback.id,
                    'timestamp': str(datetime.now()),
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            # Push Notification
            feedback_type = feedback.get_feedback_type_display()
            poc_title = f"{feedback_type} feedback added for {consultant.name} by {employee_name}"
            send_notification_for_user(consultant, request.user, poc_title, 'feedback', feedback.id)

            # Activity
            desc = f"{employee_name} added {feedback_type} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'updated')
            serializer = self.serializer_class(feedback)
            return Response({"data": serializer.data, "message": "Feedback added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            feedback = get_object_or_404(Feedback, id=kwargs.get('pk'))
            serializer = self.serializer_class(feedback, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            user_list = []
            tags = request.data.get('tagged_user', [])
            if len(tags) > 0:
                user_tag = feedback.tagged_user.all().first()
                if not user_tag:
                    tag_data = {"tags": tags, "model": "feedback", "object_id": feedback.id}
                    tag_users(tag_data)
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                    user_tag.tagged_user.add(user)

            employee_name = request.user.employee_name
            consultant = feedback.consultant
            title = f"{employee_name} tagged you in a {consultant.name}'s feedback"
            notification_data = {
                'title': title,
                'category': 'info',
                'description': title,
                'target_id': feedback.id,
                'target_type': 'feedback',
                'sender_user_type': 'user',
                'parent_id': consultant.id,
                'parent_type': 'consultant',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
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
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'sub_target': 'feedback',
                    'target_id': consultant.id,
                    'sub_target_id': feedback.id,
                    'timestamp': str(datetime.now()),
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            # Push Notification
            title = f"{serializer.data['feedback_type']} feedback updated for {consultant.name} by {employee_name}"
            send_notification_for_user(consultant, request.user, title, 'feedback', feedback.id)

            # Activity
            desc = f"{employee_name} updated {feedback.get_feedback_type_display()} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Feedback updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# API for Petition Web App
# Route - /consultant_petition/
class ConsultantPetitionAuthViewSet(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
    serializer_class = ConsultantPetitionLoginSerializer

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
        """
        try:
            email = request.data.get('email').lower()
            if email:
                consultant = get_object_or_404(Consultant, email=email)
            else:
                return Response({"error": "Email is Empty"}, status=400)
            consultant = Consultant.objects.filter(email=consultant.email, pin=request.data.get('password').strip())
            if consultant:
                consultant = consultant.first()
                if not consultant.p_is_active:
                    return Response({"error": "User account is not Active"}, status=400)
                serializer = self.serializer_class(consultant)
                return Response({"result": serializer.data}, status=202)
            return Response({"error": "Incorrect Email Id OR Password"}, status=400)
        except Exception as error:
            write_exception(message=error)
            return Response({"error": str(error)}, status=400)


# Route - /beats_consultant/
class ConsultantImportViewSet(GenericViewSet, CreateModelMixin):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantSerializer

    def create(self, request, *args, **kwargs):
        try:
            api_key = request.GET.get('api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=401)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=401)

            creator_id = User.objects.get(employee_id=1000)
            data, msg = create_consultant(request, creator_id.id)
            if msg == 'ok':
                desc = "Profile moved from Beats"
                user = User.objects.get(employee_id=1000)
                create_activity(data.id, 'consultant', user, desc, 'created')
                return Response({"message": "Consultant Created on Log1"}, status=201)
            elif msg == "exists":
                return Response({"message": "Consultant already exists, Details updated on Log1"}, status=201)
            else:
                return Response({"message": str(data)}, status=400)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": str(error)}, status=400)


# Route - /consultant/:consultant_id:/feedback
class ConsultantFeedbackViewSet(GenericViewSet, CreateModelMixin, UpdateModelMixin, ListModelMixin):
    serializer_class = FeedbackSerializer
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantFeedback.objects.all()
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query')
            feedback_type = json.loads(request.GET.get('feedback_type', '{"type":[]}'))
            first, last = get_page_limits(request)
            consultant_feedbacks = self.queryset.filter(consultant_id=kwargs.get('consultant_id'))
            if request.GET.get('project'):
                consultant_feedbacks = consultant_feedbacks.filter(project=request.GET.get('project'))
            if feedback_type['type']:
                consultant_feedbacks = consultant_feedbacks.filter(feedback_type__in=feedback_type['type'])
            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultant_feedbacks = consultant_feedbacks.filter(created_by__employee_name__icontains=query)
            serializer = self.serializer_class(consultant_feedbacks[first:last], many=True)
            return Response({"count": len(consultant_feedbacks), "data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            user_list = []
            feedback = ConsultantFeedback.objects.create(
                created_by=request.user,
                project_id=request.data.get('project'),
                rating=request.data.get('rating', None),
                consultant_id=kwargs.get('consultant_id'),
                description=request.data.get('description'),
                feedback_type=request.data.get('feedback_type'),
                department=request.data.get('department', None),
                verdict=request.data.get('verdict', None)
            )
            tags = request.data.get('tagged_user', [])
            consultant = feedback.consultant
            if len(tags) > 0 and feedback.feedback_type == 'issue':
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                tag_data = {
                    "tags": tags,
                    "object_id": feedback.id,
                    "model": "consultantfeedback",
                }
                tag_users(tag_data)
            else:
                if consultant.recruiter:
                    user_list.append(consultant.recruiter)
                if consultant.relation:
                    user_list.append(consultant.relation)
            employee_name = request.user.employee_name
            feedback_type = feedback.get_feedback_type_display()
            title_r = f"{feedback_type} feedback added for {consultant.name} by {employee_name} from {feedback.department}."
            title = f"{employee_name} tagged you in a {consultant.name}'s {feedback_type} feedback."
            notification_data = {
                'title': title if feedback_type == 'issue' else title_r,
                'category': 'info',
                'description': title,
                'target_id': feedback.id,
                'sender_user_type': 'user',
                'parent_id': consultant.id,
                'parent_type': 'consultant',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
                'target_type': 'consultantfeedback',
            }
            create_notification(user_list, notification_data)
            if feedback.feedback_type == 'pre_joining':
                pre_joining_feedback_notification(feedback)
            elif feedback.feedback_type == 'issue':
                engineering_feedback_notification(feedback)
            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'target_id': consultant.id,
                    'sub_target_id': feedback.id,
                    'timestamp': str(datetime.now()),
                    'sub_target': 'consultantfeedback',
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            # Activity
            desc = f"{employee_name} added {feedback_type} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'created')

            # Push Notification
            poc_title = f"{feedback_type} feedback added for {consultant.name} by {employee_name}"
            send_notification_for_user(consultant, request.user, poc_title, 'feedback', feedback.id)

            serializer = self.serializer_class(feedback)
            return Response({"data": serializer.data, "message": "Feedback added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            user_list = []
            feedback = get_object_or_404(ConsultantFeedback, id=kwargs.get('pk'))
            if feedback.created_by != request.user:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            serializer = self.serializer_class(feedback, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            tags = request.data.get('tagged_user', [])
            user_tag = feedback.tagged_user.all().first()
            if user_tag:
                user_tag.tagged_user.clear()
            if len(tags) > 0:
                if not user_tag:
                    tag_data = {
                        "tags": tags,
                        "object_id": feedback.id,
                        "model": "consultantfeedback",
                    }
                    tag_users(tag_data)
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                    user_tag.tagged_user.add(user)

            consultant = feedback.consultant
            employee_name = request.user.employee_name
            feedback_type = feedback.get_feedback_type_display()
            title = f"{employee_name} tagged you in a {consultant.name}'s {feedback_type} feedback"
            notification_data = {
                'title': title,
                'category': 'info',
                'description': title,
                'target_id': feedback.id,
                'sender_user_type': 'user',
                'parent_id': consultant.id,
                'parent_type': 'consultant',
                'sender_id': request.user.id,
                'recipient_user_type': 'user',
                'target_type': 'consultantfeedback',
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
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'target_id': consultant.id,
                    'sub_target_id': feedback.id,
                    'timestamp': str(datetime.now()),
                    'sub_target': 'consultantfeedback',
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            # Activity
            desc = f"{employee_name} updated {feedback.get_feedback_type_display()} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'updated')

            # Push Notification
            title = f"{feedback_type} feedback updated for {consultant.name} by {employee_name}"
            send_notification_for_user(consultant, request.user, title, 'consultantfeedback', feedback.id)
            return Response({"data": serializer.data, "message": "Feedback updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='feedback_types')
    def feedback_types(self, request, *args, **kwargs):
        return Response({"data": FEEDBACK_CHOICES}, status=200)

    @action(methods=['get'], detail=False, url_path='department')
    def department(self, request, *args, **kwargs):
        data = ['Engineering', 'Marketing', 'Legal', 'Recruitment', 'Relations', 'Finance']
        return Response({"data": data}, status=200)

    @action(methods=['get'], detail=False, url_path='project')
    def project(self, request, *args, **kwargs):
        projects = Consultant.objects.get(id=kwargs.get('consultant_id')).get_project().values(
            'id', 'submission__client', 'submission__lead__vendor_company__name')
        return Response({"data": projects}, status=200)

    @action(methods=['post'], detail=False, url_path='request_feedback')
    def request_feedback(self, request, *args, **kwargs):
        departments = request.data.get("department", [])
        consultant = Consultant.objects.get(id=kwargs.get('consultant_id'))
        projects = Project.objects.filter(
            consultant=kwargs.get('consultant_id'), statuses__status__in=['new', 'joined', 'extended', 'complete']
        ).order_by('-modified')
        if projects is None:
            projects = Project.objects.filter(
                consultant=kwargs.get('consultant_id'), statuses__status__icontains="terminate"
            ).order_by('-modified')
        obj = {
            'Legal': 'legal@consultadd.com',
            'Finance': 'finance@consultadd.com',
            'Relations': 'relations@consultadd.com',
            'Engineering': 'engineering@consultadd.com',
            'Recruitment': 'recruitment@consultadd.com',
        }
        to = list()
        if projects:
            if 'Marketing' in departments:
                to.append(projects.first().submission.created_by.email)
                to.extend(fetch_scrum_masters(projects.first().submission.created_by))
                departments.remove('Marketing')
            to = [obj[department] for department in departments]
        mail_data = {
            "cc": [], "bcc": [], "to": to,
            'template': '../templates/request_feedback.html',
            'subject': "Test mail Requesting consultant's feedback",
            'context': {
                'consultant_name': consultant.name,
                'sender_name': request.user.employee_name,
                'link': f'https://app.log1.com/#/consultant/bench/{kwargs.get("consultant_id")}?key=feedback',
                'feedback_type': request.data['feedback_type']
            },
        }
        if os.environ.get('ENV', 'local') == 'prod':
            send_email(mail_data, request.user.email)
        return Response({"message": "mail sent"}, status=201)
