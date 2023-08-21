import csv
from django.db import transaction
from django.http import HttpResponse
from django.db.models import Subquery, OuterRef

from rest_framework.mixins import *
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from consultant.utils import *
from api_key.models import APIKey
from consultant.serializers import *
from employee.models import tag_users
from project.utils import fetch_scrum_masters

from utils_app.utils import get_timezone
from utils_app.ms_account import MicrosoftAccount
from attachment.serializers import AttachmentSerializer
from utils_app.utils import get_timezone, add_export_log
from activity.serializers import Activity, ActivitySerializer
from project.models import ProjectStatus, ConsultantFeedback, FEEDBACK_CHOICES
from log1.utils import get_page_limits, write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG


# Route - /v2/consultant/<consultant_id>/microsoft/
class MicroSoftViewSet(GenericViewSet, CreateModelMixin, DestroyModelMixin):
    queryset = MSAccount.objects.all()
    serializer_class = MSAccountSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('consultant_id'))
            ms = MicrosoftAccount()
            if hasattr(consultant, 'msaccount'):
                account = consultant.msaccount
                licence = ms.assign_licence(account.user_id)
                if licence == 'ok':
                    account.licence_assigned = True
                    member_id, msg = ms.assign_team(account.user_id)
                    if msg == 'ok':
                        account.member_id = member_id
                account.save()
            else:
                account = MSAccount.objects.create(
                    consultant=consultant,
                    email=f"{consultant.name[0]}.{consultant.name[0]}@consultadd.com"
                )
                name = consultant.name.split()
                data = {
                    "first_name": name[0],
                    "name": consultant.name,
                    "email": consultant.email,
                    "password": f"consultadd@1{consultant.id}23",
                    "last_name": name[1] if len(name) > 1 else "",
                }
                user_id, msg = ms.create_account(data)
                if msg == 'ok':
                    account.user_id = user_id
                    licence = ms.assign_licence(user_id)
                    if licence == 'ok':
                        account.licence_assigned = True
                        member_id, msg = ms.assign_team(user_id)
                        if msg == 'ok':
                            account.member_id = member_id
                account.save()

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('consultant_id'))
            ms = MicrosoftAccount()
            if hasattr(consultant, 'msaccount'):
                account = consultant.msaccount
                msg = ms.remove_member(account.member_id)
                if msg == 'ok':
                    msg = ms.remove_licence(account.user_id)
                    if msg == 'ok':
                        account.licence_assigned = False
                        ms.disable_account(account.user_id)
                        account.save()
                return Response({"message": "Microsoft account removed"}, status=400)
            else:
                return Response({"message": "Microsoft account not found"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /v2/consultant/
class ConsultantV2ViewSets(ModelViewSet):
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

            if sort_by in ['name', '-created']:
                consultants = consultants.order_by(sort_by)
            data = list()
            for i in consultants.exclude(status='terminated'):
                data.append(i)
            for i in consultants.filter(status='terminated'):
                data.append(i)
            serializer = ConsultantV2ListSerializer(data[first:last], many=True)
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
            add_export_log("Consultant Info", request)
            return response
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant/
class ConsultantViewSets(ModelViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

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
                work_type=F('submission__work_type'),
                consultant_name=F('consultant__name'),
                job_title=F('submission__lead__job_title'),
                status=Subquery(project_status.values('status')[:1]),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'consultant_name', 'city', 'company_name', 'client', 'rate', 'marketer_name', 'created',
                     'status', 'employer', 'start_date', 'end_date', 'job_title', 'is_remote', 'work_type')
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

            if 'superadmin' not in roles:
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
        if not ('superadmin' in roles or 'finance' in roles):
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
                country=data['country'],
                phone_no=data['phone_no'],
                current_city=data['current_city'],
                date_of_birth=data['date_of_birth'],
                skype=request.data.get('skype', None),
                links=request.data.get('links', None),
                work_type=request.data.get('work_type', 'full_time'),
                marital_status=request.data.get('marital_status', None),
                internal_employee=request.data.get('internal_employee', False)
            )
            if consultant.current_city:
                consultant.timezone = get_timezone(consultant.current_city)
                consultant.save()

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
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles or 'legal' in roles):
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
                "country": "Country",
                "phone_no": "Phone No",
                "current_city": "Current City",
                "date_of_birth": "Date of Birth",
                "marital_status": "Marital Status",
                "internal_employee": "Internal Employee"
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
            ).order_by('-created')
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
        try:
            filter_by_status = request.GET.get("filter_by_status", None)
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
                prev_rate = 0
                qs = ConsultantRateRevision.objects.filter(consultant_id=request.data['consultant'], end=None)
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

                # Push Notification
                title = f"{rate_obj.consultant.name}'s rate revised to {rate_obj.rate} by {request.user.employee_name}"
                send_notification_for_user(rate_obj.consultant, request.user, title, 'consultantraterevision')

                # Activity
                desc = f"{request.user.employee_name.title()} revised rate from {prev_rate} to {rate_obj.rate}"
                create_activity(rate_obj.consultant.id, 'consultant', request.user, desc, 'updated')

                serializer = ConsultantRateRevisionSerializer(rate_obj)
                return Response({"data": serializer.data, "message": "Rate revised"}, status=201)
            except Exception as error:
                write_exception(error, request)
                return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='margin')
    def margin(self, request, pk):
        try:
            projects = Project.objects.filter(statuses__status='joined', statuses__is_current=True)
            qs = Project.objects.filter(
                Q(statuses__status__in=['joined', 'complete'], statuses__is_current=True) |
                Q(statuses__status__istartswith='terminated', statuses__is_current=True)
            ).filter(
                Q(consultant_id=pk) |
                Q(submission__consultant_marketing__consultant_id=pk)
            ).order_by('-start_date')
            projects = projects.filter(
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

            for project in qs:
                project_data.append(
                    {
                        "id": project.id,
                        "rate": project.rate,
                        "status": project.status,
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

            teams_marketer = request.data.get('teams_marketer', [])
            for data in teams_marketer:
                team_id = data.get('team')
                marketers_value = data.get('marketers')

                team = get_object_or_404(Team, id=team_id)

                if marketers_value == ["all"]:
                    marketer_ids = User.objects.filter(
                        is_active=True,
                        account_login=True,
                        team=team
                    ).values_list('id', flat=True)
                else:
                    marketer_ids = marketers_value

                consultant_marketing.teams.add(team)

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
            if 'superadmin' or 'recruiter' in request.user.roles:
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

    @action(methods=['get'], detail=True, url_path='assigned_marketers')
    def assigned_marketers(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset.exists():
                marketer_data = {}

                marketers = queryset.first().marketer.all()
                teams = queryset.first().teams.all()

                for team in teams:
                    if team.name in marketer_data:
                        continue
                    else:
                        team_info = {
                            'team_id': team.id,
                            'team_name': team.name,
                            'marketers': []
                        }
                        marketer_data[team.name] = team_info

                for marketer in marketers:

                    if marketer.team:
                        team = get_object_or_404(Team, id=marketer.team.id)

                        marketer_info = {
                            'id': marketer.id,
                            'name': marketer.employee_name
                        }
                        if team in teams:
                            marketer_data[team.name]['marketers'].append(marketer_info)


                for team_info in marketer_data.values():
                    team_marketer_ids = set(marketer['id'] for marketer in team_info['marketers'])

                    all_marketers_info = User.objects.filter(
                        is_active=True,
                        account_login=True,
                        team__name=team_info['team_name']
                    ).values('id', 'employee_name')

                    marketer_ids_set = set(marketer['id'] for marketer in all_marketers_info)
                    if marketer_ids_set and marketer_ids_set.issubset(team_marketer_ids):
                        team_info['is_all'] = True
                    else:
                        team_info['is_all'] = False
                    team_info['all_marketers'] = all_marketers_info

                return Response({"data": list(marketer_data.values())}, status=200)
            else:
                return Response({"message": "Consultant is not in Marketing"}, status=404)
            # if 'superadmin' in request.user.roles:
            #     return Response({"data": serializer.data, "message": "Team removed"}, status=202)
            # else:
            #     return Response({"message": DONT_HAVE_ACCESS}, status=403)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='updated_marketers')
    def updated_marketers(self, request, pk):
        try:
            queryset = ConsultantMarketing.objects.filter(id=pk)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"message": "Consultant is not in Marketing"})
            if  'superadmin' or 'recruiter' in request.user.roles:
                teams_marketer = request.data.get('teams_marketer', [])

                updated_team_ids = {data['team'] for data in teams_marketer}
                updated_marketer_ids = set()  # Initialize an empty set to store the updated marketer IDs

                for data in teams_marketer:
                    if "all" in data['marketers']:
                        # If "all" is present, fetch all marketer IDs for the specified team and add them to updated_marketer_ids
                        team = data['team']
                        marketer_ids = User.objects.filter(
                            is_active=True,
                            account_login=True,
                            team=team
                        ).values_list('id', flat=True)
                        updated_marketer_ids.update(marketer_ids)
                    else:
                        # Add individual marketer IDs to updated_marketer_ids
                        updated_marketer_ids.update(data['marketers'])

                existing_team_ids = set(consultant_marketing.teams.values_list('id', flat=True))
                existing_marketer_ids = set(consultant_marketing.marketer.values_list('id', flat=True))

                add_teams_ids = updated_team_ids - existing_team_ids
                add_marketers_ids = updated_marketer_ids - existing_marketer_ids

                removed_teams_ids = existing_team_ids - updated_team_ids
                removed_marketers_ids = existing_marketer_ids-updated_marketer_ids

                if add_teams_ids:
                    teams = Team.objects.filter(id__in=add_teams_ids)
                    consultant_marketing.teams.add(*teams)
                    add_teams_names = Team.objects.filter(id__in=add_teams_ids).values_list('name', flat=True)

                if add_marketers_ids:
                    marketers = User.objects.filter(id__in=add_marketers_ids)
                    consultant_marketing.marketer.add(*marketers)
                    add_marketers_names = User.objects.filter(
                        id__in=add_marketers_ids).values_list('employee_name', flat=True)

                if removed_teams_ids:
                    teams = Team.objects.filter(id__in=removed_teams_ids)
                    consultant_marketing.teams.remove(*teams)
                    remove_teams_names = Team.objects.filter(id__in=removed_teams_ids).values_list('name', flat=True)

                if removed_marketers_ids:
                    marketers = User.objects.filter(id__in=removed_marketers_ids)
                    consultant_marketing.marketer.remove(*marketers)
                    remove_marketers_names = User.objects.filter(id__in=removed_marketers_ids).values_list(
                        'employee_name',
                        flat=True)

                consultant_marketing.save()

                if len(add_marketers_ids) > 1:
                    marketer_str = "marketers"
                else:
                    marketer_str = "marketer"

                if len(add_teams_ids) > 1:
                    team_str = "teams"
                else:
                    team_str = "team"


                employee_name = request.user.employee_name

                # Initialize a list to store activity descriptions
                employee_description_parts = ""

                if add_teams_ids:
                    employee_description_parts += f"assigned {team_str} - {', '.join(add_teams_names)}. "

                if add_marketers_ids:
                    employee_description_parts += f"assigned {marketer_str} - {', '.join(add_marketers_names)}. "

                if removed_marketers_ids:
                    employee_description_parts += f"removed  {marketer_str} - {', '.join(remove_marketers_names)}. "

                if removed_teams_ids:
                    employee_description_parts += f"removed {team_str} - {', '.join(remove_teams_names)}. "

                if employee_description_parts:
                    # Combine employee-related activity descriptions into a single message
                    employee_activity_description = f"{employee_name} - {employee_description_parts}"
                    create_activity(
                        consultant_marketing.consultant.id, 'consultant', request.user,
                        employee_activity_description, 'updated'
                    )
                    send_notification_for_user(consultant_marketing.consultant, request.user, f"{employee_name} update the consultant marketing",
                                               'consultantmarketing')

                return Response({"message": "Successfully updated"}, status=202)
            else:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='in_pool')
    def in_pool(self, request, pk):
        try:
            try:
                consultant_marketing = ConsultantMarketing.objects.get(id=pk, status="open")
                in_pool = request.GET.get('in_pool',False)
                consultant_marketing.in_pool = in_pool
                consultant_marketing.save()
            except ConsultantMarketing.DoesNotExist:
                # Handle the case where the consultant is not found
                return Response({"error": "Marketing cycle not found"}, status=404)

            action = "added to pool" if in_pool else "removed from pool"
            desc = f"{consultant_marketing.consultant.name} {action} by {request.user.employee_name}"
            create_activity(consultant_marketing.consultant.id, 'consultant', request.user, desc, 'updated')
            return Response({"message": "Updated in pool status"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /consultant_profile/
class ConsultantProfileViewSets(ModelViewSet):
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
            poc_type = request.data['poc_type']
            if poc_type == 'relation':
                poc_type = 'retention'

            queryset = ConsultantPOC.objects.filter(poc_type=poc_type, consultant=request.data['consultant'], end=None)

            if queryset:
                previous_poc = queryset.first()
                previous_poc.end = date.today()
                previous_poc.save()

            poc = ConsultantPOC.objects.create(
                poc_type=poc_type,
                start=date.today(),
                poc_id=request.data['poc'],
                consultant_id=request.data['consultant'],
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
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles or 'legal' in roles):
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        try:
            instance = WorkAuth.objects.filter(consultant=request.data['consultant'], is_current=True)
            if instance:
                previous_work_auth = instance.first()
                previous_work_auth.is_current = False
                previous_work_auth.save()
            work_auth = WorkAuth.objects.create(
                is_current=True,
                visa_type=request.data['visa_type'],
                visa_start=request.data['visa_start'],
                consultant_id=request.data['consultant'],
                visa_end=request.data.get('visa_end', None),
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
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles or 'finance' in roles or 'legal' in roles):
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
                profile.visa_end = serializer.data['visa_end']
                profile.visa_start = serializer.data['visa_start']
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
            first, last = get_page_limits(request)
            feedback_type = json.loads(request.GET.get('feedback_type', '[]'))
            queryset = self.queryset.filter(consultant_id=kwargs.get('consultant_id'))
            if request.GET.get('project'):
                queryset = queryset.filter(project_id=request.GET.get('project'))
            if feedback_type:
                queryset = queryset.filter(feedback_type__in=feedback_type)
            if query:
                query = query.lstrip().replace(':amp:', '&')
                queryset = queryset.filter(created_by__employee_name__icontains=query)
            serializer = self.serializer_class(queryset[first:last], many=True)
            return Response({"count": len(queryset), "data": serializer.data}, status=200)
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
                verdict=request.data.get('verdict', None),
                consultant_id=kwargs.get('consultant_id'),
                description=request.data.get('description'),
                feedback_type=request.data.get('feedback_type'),
                department=request.data.get('department', None),
            )
            if feedback.feedback_type in ['engineering_issue', '2_week', 'independent']:
                setattr(feedback, 'department', 'engineering')
                feedback.save()
            #     if feedback.feedback_type == 'engineering_issue':
            #         MessageCard.feedback_card(feedback, request)
            #
            # elif feedback.feedback_type == 'pre_joining':
            #     MessageCard.feedback_card(feedback, request)

            consultant = feedback.consultant
            emp_name = request.user.employee_name
            feedback_type = feedback.get_feedback_type_display()

            # Tagging notification
            tags = request.data.get('tagged_user', [])
            if len(tags) > 0:
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                tag_data = {
                    "tags": tags,
                    "object_id": feedback.id,
                    "model": "consultantfeedback",
                }
                tag_users(tag_data)

            title = f"{emp_name} tagged you in a {consultant.name}'s {feedback_type} feedback."
            create_and_send_notification(consultant, feedback, title, user_list, request)

            # POC Notification
            pocs = consultant.pocs.all()
            user_list = [user.poc for user in pocs]
            title = f"{feedback_type} feedback added for {consultant.name} by {emp_name} from {feedback.department}."
            create_and_send_notification(consultant, feedback, title, user_list, request)

            # Activity
            desc = f"{emp_name} added {feedback_type} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'created')

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

            consultant = feedback.consultant
            employee_name = request.user.employee_name
            feedback_type = feedback.get_feedback_type_display()

            # Tagging notification
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

            title = f"{employee_name} tagged you in a {consultant.name}'s {feedback_type} feedback"
            create_and_send_notification(consultant, feedback, title, user_list, request)

            # Push Notification
            pocs = consultant.pocs.all()
            user_list = [user.poc for user in pocs]
            title = f"{feedback_type} feedback updated for {consultant.name} by {employee_name}"
            create_and_send_notification(consultant, feedback, title, user_list, request)

            # Activity
            desc = f"{employee_name} updated {feedback.get_feedback_type_display()} feedback"
            create_activity(consultant.id, 'consultant', request.user, desc, 'updated')

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
    def project(self, request, consultant_id):
        try:
            projects = Consultant.objects.get(id=consultant_id).get_project().annotate(
                vendor=F('submission__lead__vendor_company__name'),
                client=F('submission__client'),
            ).values('id', 'client', 'vendor')
            return Response({"data": projects}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='request_feedback')
    def request_feedback(self, request, consultant_id):
        try:
            departments = request.data.get("department", [])
            consultant = Consultant.objects.get(id=consultant_id)
            projects = Project.objects.filter(
                consultant=consultant_id, statuses__status__in=['new', 'joined', 'extended', 'complete']
            ).order_by('-modified')
            if not projects:
                projects = Project.objects.filter(
                    consultant=consultant_id, statuses__status__icontains="terminate"
                ).order_by('-modified')
            obj = {
                'Legal': 'legal@consultadd.com',
                'Finance': 'finance@consultadd.com',
                'Relations': 'relations@consultadd.com',
                'Engineering': 'engineering@consultadd.com',
                'Recruitment': 'recruitment@consultadd.com',
            }

            to = list()
            if projects and 'Marketing' in departments:
                to.append(projects.first().submission.created_by.email)
                to.extend(fetch_scrum_masters(projects.first().submission.created_by))

            to = [obj[department] for department in departments if 'Marketing' != department] + to
            mail_data = {
                "to": to, "cc": [], "bcc": [],
                'template': '../templates/request_feedback.html',
                'subject': "Test mail Requesting consultant's feedback",
                'context': {
                    'consultant_name': consultant.name,
                    'sender_name': request.user.employee_name,
                    'feedback_type': request.data['feedback_type'],
                    'link': f'https://app.log1.com/#/consultant/bench/{consultant_id}?key=feedback',
                },
            }
            if os.environ.get('ENV', 'local') == 'prod':
                send_email(mail_data, request.user.email)
            return Response({"message": "mail sent"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# API for Petition Web App
# Route - /consultant_petition/
class ConsultantPetitionAuthViewSet(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
    serializer_class = ConsultantPetitionLoginSerializer

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        try:
            email = request.data.get('email', None)
            if email:
                consultant = Consultant.objects.filter(email=email.lower())
                if not consultant:
                    return Response({"error": "User not found"}, status=404)
                consultant = consultant.first()
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


# Route - /log1_consultant/
class ConsultantPerformanceViewSet(GenericViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantPetitionLoginSerializer

    @staticmethod
    def verify_api_key(api_key):
        if not APIKey.objects.is_valid(api_key):
            return Response({"message": "Unauthorized"}, status=401)
        return True

    @action(methods=['GET'], detail=False, url_path='project')
    def project(self, request):
        self.verify_api_key(request.GET['api_key'])
        try:
            data = []
            email = request.GET.get('email')
            consultant = get_object_or_404(Consultant, email=email)
            projects = consultant.projects.all()
            for project in projects:
                feedbacks = []
                engineering_feedbacks = project.feedbacks.filter(department__iexact='engineering')
                for feedback in engineering_feedbacks:
                    feedbacks.append({
                        "created_date": feedback.created,
                        "description": feedback.description,
                        "name": feedback.created_by.employee_name
                    })
                project_data = {
                    "rate": project.rate,
                    "feedback": feedbacks,
                    "location": project.city,
                    "status": project.status,
                    "end_date": project.end_date,
                    "start_date": project.start_date,
                    "client": project.submission.client,
                    "job_title": project.submission.lead.job_title,
                    "is_remote": True if project.is_remote else False,
                    "marketer_name": project.created_by.employee_name,
                    "work_type": project.submission.get_work_type_display()
                }
                data.append(project_data)
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(message=error)
            return Response({"data": []}, status=200)

    @action(methods=['GET'], detail=False, url_path='feedback')
    def feedback(self, request):
        self.verify_api_key(request.GET['api_key'])
        try:
            email = request.GET.get('email')
            consultant = get_object_or_404(Consultant, email=email)
            feedback_queryset = ConsultantFeedback.objects.filter(consultant=consultant)
            serializer = FeedbackSerializer(feedback_queryset, many=True)
            return Response({"data": serializer.data, "count": len(serializer.data)}, status=200)
        except Exception as error:
            write_exception(message=error)
            return Response({"data": []}, status=200)
