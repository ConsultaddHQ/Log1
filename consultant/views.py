import logging
from datetime import date, datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Subquery, OuterRef, Q, Count

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin

from constance import config
from consultant.serializers import *
from marketing.models import Interview
from project.models import Project, ProjectStatus
from attachment.serializers import AttachmentSerializer
from utils_app.utils import post_msg_using_webhook, html_to_text
from notification.views import create_notification, push_notification

logger = logging.getLogger(__name__)
dont_have_access = 'you don\'t have access'


def close_marketing():
    try:
        queryset = ConsultantMarketing.objects.filter(end__lte=date.today(), status='open')
        queryset.update(status='close')
        return None
    except Exception as error:
        return error


def start_marketing():
    try:
        queryset = ConsultantMarketing.objects.filter(start__lte=date.today(), status='close', end=None)
        queryset.update(status='open')
        return None
    except Exception as error:
        return error


def send_exit_interview_detail(terminate):
    try:
        # Mattermost message for Exit Interview
        exit_details = html_to_text(terminate.exit_details)
        reason = ", ".join(reason.name for reason in terminate.reasons.all())
        text = f"#### Exit interview for {terminate.consultant.name}\n" \
               f"**Reason for leaving** : {reason}\n" \
               f"**Termination Date** : {terminate.last_date}\n" \
               f"**Exit Interview Details** : {exit_details} \n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text,
        }
        post_msg_using_webhook(config.exit_interview_url, data)
        return None
    except Exception as error:
        return error


def terminate_consultant(terminate):
    try:
        consultant = terminate.consultant
        consultant.status = 'terminated'
        consultant.save()

        marketings = consultant.marketing.filter(status='open')
        for marketing in marketings:
            marketing.status = 'close'
            marketing.end = date.today()
            marketing.save()

        terminate.status = 'complete'
        terminate.save()

        # Email for Exit Process Cancelled
        res = "Development Server"
        if os.environ.get('ENV', 'local') == 'prod':
            res, error = send_exit_process_mail(terminate, 'complete')
            if error == 'error':
                logger.error(res)

        # App Notification
        recruiter = consultant.recruiter
        user_list = [recruiter]
        scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
        for user in scrum_masters:
            user_list.append(user)

        title = f"{consultant.name} got terminated on {terminate.last_date}"

        notification_data = {
            'category': 'info',
            'sender_user_type': 'user',
            'target_type': 'consultant',
            'recipient_user_type': 'user',
            'description': terminate.type,
            'title': title,
            'sender_id': terminate.created_by.id,
            'target_id': terminate.consultant.id,
        }
        create_notification(user_list, notification_data)

        # Push Notification
        message_body = {
            "category": "alert",
            "show_in_foreground": True,
            "click_action": "https://app.log1.com",
            "body": title,
            "title": title,
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target': 'consultant',
                'timestamp': str(timezone.now()),
                'target_id': terminate.consultant.id,
            },
        }

        object_ids = []
        for user in user_list:
            object_ids.append(user.id)

        registration_ids = list(
            FCMDevice.objects.filter(object_id__in=list(object_ids), content_type__model='user'
                                     ).values_list('device_id', flat=True))
        push_notification(registration_ids, message_body)
        return None
    except Exception as error:
        return error


def send_exit_process_mail(terminate, exit_status):
    try:
        consultant = terminate.consultant
        recruiter = consultant.recruiter
        if consultant.relation:
            poc = consultant.relation
        else:
            poc = consultant.recruiter

        to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL]
        cc = [poc.email, config.SUPERADMIN]

        scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
        for user in scrum_masters:
            cc.append(user.email)

        marketings = consultant.marketing.filter(status='open')
        for marketing in marketings:
            cc.append(marketing.primary_marketer.email)

        types = dict(EXIT_TYPE_CHOICE)

        if terminate.reasons.all():
            reason = ", ".join(reason.name for reason in terminate.reasons.all())
        else:
            reason = 'NA'

        subject = f'Exit Process Initiated for {consultant.name}'
        title = "Exit Process Initiated"

        if exit_status == 'cancel':
            subject = f'Exit Process Cancelled for {consultant.name}'
            title = "Exit Process Cancelled"

        elif exit_status == 'complete':
            subject = f'{consultant.name} Terminated'
            title = "Exit Process Complete, Employee Terminated"

        exit_details = html_to_text(terminate.exit_details)
        mail_data = {
            'to': to,
            'cc': cc,
            'bcc': [],
            'subject': subject,
            'template': '../templates/exit_process.html',
            'context': {
                'title': title,
                'reason': reason,
                'exit_status': exit_status,
                'type': types[terminate.type],
                'consultant': consultant.name,
                'consultant_email': consultant.email,
                'recruiter': recruiter.employee_name,
                'rehire': 'Yes' if terminate.rehire else 'No',
                'legal': 'Yes' if terminate.legal_action else 'No',
                'exit_details': exit_details if terminate.exit_details else 'NA',
                'last_date': terminate.last_date if terminate.last_date else 'NA',
                'resign_date': terminate.resign_date if terminate.resign_date else 'NA',
                'cancel_reason': terminate.cancel_reason if terminate.cancel_reason else 'NA',
                'notice_period': terminate.notice_period if terminate.legal_action else 'NA',
            },
        }
        res = send_email(mail_data, terminate.created_by.email)
        return res, "ok"
    except Exception as error:
        logger.error(error)
        return error, "error"


class ConsultantViewSets(viewsets.ModelViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    sub_serializer_class = ConsultantSubmissionSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def get_submission_data(queryset, filter_by_status, first, last):
        try:
            total = queryset.count()
            submission = queryset.filter(status='sub').count()
            project = queryset.filter(status='project').count()
            interview = queryset.filter(status='interview').count()

            if filter_by_status:
                queryset = queryset.filter(status=filter_by_status)

            data_counts = {
                'total': total,
                'sub': submission,
                'project': project,
                'interview': interview
            }
            data = queryset[first:last].annotate(
                consultant_name=F('consultant_marketing__consultant__name'),
                company_name=F('lead__vendor_company__name'),
                marketer_name=F('created_by__employee_name'),
                city=F('lead__city')
            ).values('id', 'rate', 'consultant_name', 'company_name', 'marketer_name', 'city', 'project', 'client')

            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, "error"

    @staticmethod
    def get_interview_data(queryset, filter_by_status, first, last):
        try:
            # Interview counts by status
            queryset = queryset.order_by('-modified').distinct('modified')
            total = queryset.count()
            failed = queryset.filter(status='failed').count()
            offer = queryset.filter(status='offer').count()
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
                job_title=F('submission__lead__job_title'),
                ctb=F('supervisor__employee_name'),
                client=F('submission__client'),
                project=F('submission__project'),
                marketer_name=F('submission__created_by__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),

            ).values('id', 'round', 'status', 'start_time', 'end_time', 'interview_mode', 'submission_id', 'status',
                     'ctb', 'marketer_name', 'consultant_name', 'client', 'company_name',
                     'project', 'job_title', 'modified', 'created')

            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    @staticmethod
    def get_project_data(queryset, filter_by_status, first, last):
        try:
            # count of project by status
            total = queryset.count()
            new = queryset.filter(statuses__status='new', statuses__is_current=True).count()
            joined = queryset.filter(statuses__status='joined', statuses__is_current=True).count()
            received = queryset.filter(statuses__status='received', statuses__is_current=True).count()
            on_boarded = queryset.filter(statuses__status='on_boarded', statuses__is_current=True).count()
            not_joined = queryset.filter(statuses__status='not_joined', statuses__is_current=True).count()

            queryset = queryset.order_by('-modified').distinct('modified')
            if filter_by_status:
                queryset = queryset.filter(statuses__status=filter_by_status, statuses__is_current=True)

            data_counts = {
                'new': new,
                'total': total,
                'joined': joined,
                'received': received,
                'on_boarded': on_boarded,
                'not_joined': not_joined,
            }
            project_status = ProjectStatus.objects.filter(
                project=OuterRef("pk"), is_current=True)

            data = queryset[first:last].annotate(
                rate=F('submission__rate'),
                client=F('submission__client'),
                employer=F('submission__employer'),
                consultant_name=F('consultant__name'),
                status=Subquery(project_status.values('status')[:1]),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'consultant_name', 'city', 'company_name', 'client', 'rate', 'marketer_name', 'created',
                     'status', 'employer', 'start_date', 'end_date')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    def list(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            query = request.query_params.get('query', None)
            consultants = Consultant.objects.filter(marketing__status='open')
            roles = request.user.roles

            if 'marketer' in request.user.roles:
                consultants = consultants.filter(
                    Q(marketing__in_pool=True, marketing__status='open') |
                    Q(marketing__marketer=request.user, marketing__status='open')
                )
            elif 'admin' in roles or 'proxy' in roles:
                consultants = consultants.filter(
                    Q(marketing__teams=request.user.team, marketing__in_pool=False, marketing__status='open') |
                    Q(marketing__in_pool=True, marketing__status='open')
                )

            elif 'recruiter' in roles:
                consultants = consultants.filter(
                    pocs__poc=request.user
                )

            if query:
                consultants = consultants.filter(name__istartswith=query)

            consultants = consultants.order_by('id').distinct('id')
            serializer = ConsultantListSerializer(consultants, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            consultant_id = kwargs.get('pk')
            submission = request.query_params.get('submission', 'false')
            if submission.lower() == "true":
                consultant = get_object_or_404(Consultant, id=consultant_id)
                serializer = self.sub_serializer_class(consultant)
            else:
                consultant = get_object_or_404(Consultant, id=consultant_id)
                serializer = self.serializer_class(consultant)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        consultant = Consultant.objects.filter(email__iexact=data['email'])
        if consultant:
            return Response({"result": "Consultant Already Exist"}, status=status.HTTP_400_BAD_REQUEST)
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
                links=data['links'],
                consultant=consultant,
                visa_end=data['visa_end'],
                profile_owner=request.user,
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
                current_city=data['current_city'],
                date_of_birth=data['date_of_birth'],
            )

            # Creating Recruiter of Consultant
            ConsultantPOC.objects.create(
                consultant=consultant,
                poc_type='recruiter',
                start=timezone.now(),
                poc_id=data['recruiter']
            )

            # Creating Retention of Consultant
            if request.data.get('retention', None):
                ConsultantPOC.objects.create(
                    consultant=consultant,
                    poc_type='retention',
                    start=timezone.now(),
                    poc_id=data['retention']
                )

            # Creating Work-Auth
            WorkAuth.objects.create(
                consultant=consultant,
                is_current=True,
                visa_end=data['visa_end'],
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
            )

        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"result": ConsultantSerializer(consultant).data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        try:
            obj = get_object_or_404(Consultant, id=kwargs.get('pk'))
            serializer = ConsultantUpdateSerializer(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='set_password')
    def set_consultant_password(self, request):
        try:
            if request.user.is_superuser:
                consultant = get_object_or_404(Consultant, id=request.data['consultant_id'])
                consultant.set_password(request.data['new_password'])
                consultant.save()
                return Response({'result': {'message': 'Password Changed Successfully'}}, status=status.HTTP_200_OK)
            else:
                return Response({'result': {'message': 'Unauthorized Access'}}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='search')
    def search(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('query', None)
            if query:
                consultants = Consultant.objects.filter(name__istartswith=query).order_by('name')
            else:
                consultants = Consultant.objects.all().order_by('name')
            data = consultants[:10].values('id', 'name', 'email')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post', 'put'], detail=True, url_path='education')
    def education(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'POST':
            try:
                data = request.data
                education = Education.objects.create(
                    city=data['city'],
                    title=data['title'],
                    major=data['major'],
                    remark=data['remark'],
                    org_name=data['org_name'],
                    edu_type=data['edu_type'],
                    end_date=data['end_date'],
                    start_date=data['start_date'],
                    consultant_id=kwargs.get('pk'),
                )
                serializer = EducationSerializer(education)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                education = get_object_or_404(Education, id=kwargs.get('pk'))
                serializer = EducationSerializer(education, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post', 'put'], detail=True, url_path='experience')
    def experience(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'POST':
            try:
                data = request.data
                experience = Experience.objects.create(
                    city=data['city'],
                    title=data['title'],
                    remark=data['remark'],
                    company=data['company'],
                    exp_type=data['exp_type'],
                    end_date=data['end_date'],
                    start_date=data['start_date'],
                    consultant_id=kwargs.get('pk'),
                )
                serializer = ExperienceSerializer(experience)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                experience = get_object_or_404(Experience, id=kwargs.get('pk'))
                serializer = ExperienceSerializer(experience, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='marketing')
    def marketing(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        marketing_stage = request.query_params.get('stage')
        page_size = int(request.query_params.get("page_size", 10))
        filter_by_status = request.query_params.get("filter_by_status", None)
        last, first = page * page_size, page * page_size - page_size

        try:
            consultant_id = kwargs.get('pk')
            if marketing_stage == 'interview':
                interviews = Interview.objects.filter(
                    submission__consultant_marketing__end=None,
                    submission__consultant_marketing__status='open',
                    submission__consultant_marketing__consultant_id=consultant_id,
                )
                data, counts = self.get_interview_data(interviews, filter_by_status, first, last)
                if counts == "error":
                    return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                projects = Project.objects.filter(
                    consultant_id=consultant_id
                )
                data, counts = self.get_project_data(projects, filter_by_status, first, last)
                if counts == "error":
                    return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"results": data, "total": counts})
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='documents')
    def documents(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk'))
            queryset = consultant.attachments.all()
            serializer = AttachmentSerializer(queryset, many=True)
            return Response({'results': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get', 'post'], detail=True, url_path='rate_revision')
    def rate_revision(self, request, *args, **kwargs):
        if request.method == 'GET':
            try:
                rate_revision = ConsultantRateRevision.objects.filter(consultant=kwargs.get('pk')).order_by('-id')
                data = rate_revision.values('id', 'rate', 'start', 'end', 'previous_rate', 'feedback', 'consultant')
                return Response({"results": data}, status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                prev_rate_obj = ConsultantRateRevision.objects.filter(
                    consultant_id=request.data['consultant'], end=None
                )
                prev_rate = 0
                if prev_rate_obj:
                    prev_rate_obj = prev_rate_obj.first()
                    prev_rate_obj.end = datetime.today()
                    prev_rate_obj.save()
                    prev_rate = prev_rate_obj.rate
                rate_obj = ConsultantRateRevision.objects.create(
                    previous_rate=prev_rate,
                    rate=request.data['rate'],
                    start=request.data['start'],
                    feedback=request.data['feedback'],
                    consultant_id=request.data['consultant']
                )
                serializer = ConsultantRateRevisionSerializer(rate_obj)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantBenchViewSets(ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='map')
    def map(self, request):
        consultants = Consultant.objects.filter(
            marketing__status='open'
        ).values('current_city').annotate(total=Count('current_city')).order_by('current_city')
        return Response({"results": consultants}, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        team_name = request.query_params.get('team', None)
        location = request.query_params.get('location', None)
        con_status = request.query_params.get('status', 'all')
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            consultants = Consultant.objects.exclude(status__in=['archived', 'terminated'])
            # Team wise Filter
            if team_name and team_name != 'all' and team_name.lower() != 'consultadd':
                consultants = consultants.filter(marketing__teams__name=team_name, marketing__status='open')

            # Location wise Filter
            if location:
                con_status = 'in_marketing'
                consultants = consultants.filter(
                    current_city=location,
                )

            # Consultants search based on name, email, recruiter and location
            elif query:
                consultants = consultants.filter(
                    Q(email__iexact=query) |
                    Q(name__icontains=query) |
                    Q(skills__istartswith=query) |
                    Q(current_city__istartswith=query) |
                    Q(pocs__poc__employee_name__istartswith=query, pocs__end=None)
                )

            consultants = consultants.order_by('id').distinct('id')

            total = consultants.all()

            on_project = consultants.filter(status='on_project')

            open_candidates = list(ConsultantMarketing.objects.filter(
                status='open'
            ).order_by('consultant_id').distinct('consultant_id').values_list('consultant_id', flat=True))

            candidate = consultants.filter(status='on_bench').exclude(id__in=open_candidates)

            in_pool = consultants.filter(marketing__status='open', marketing__in_pool=True)

            in_marketing = consultants.filter(marketing__status='open', marketing__in_pool=False)

            count = {
                "total": total.count(),
                "in_pool": in_pool.count(),
                "on_project": on_project.count(),
                "in_marketing": in_marketing.count(),
                "candidate": candidate.count() if candidate.count() > 0 else 0
            }

            # Filter Consultant by status and In pool
            if con_status == 'all':
                consultants = total
            elif con_status == 'in_marketing':
                consultants = in_marketing
            elif con_status == 'in_pool':
                consultants = in_pool
            elif con_status == 'candidate':
                consultants = candidate
            elif con_status == 'on_project':
                consultants = on_project

            poc = ConsultantPOC.objects.filter(
                consultant=OuterRef("pk"), end=None, poc_type='recruiter')

            rate = ConsultantRateRevision.objects.filter(
                consultant=OuterRef("pk"), end=None)

            marketing = ConsultantMarketing.objects.filter(
                consultant=OuterRef("pk"), status='open')

            data = consultants[first:last].annotate(
                rate=Subquery(rate.values('rate')[:1]),
                rtg=Subquery(marketing.values('rtg')[:1]),
                in_pool=Subquery(marketing.values('in_pool')[:1]),
                marketing_start=Subquery(marketing.values('start')[:1]),
                recruiter=Subquery(poc.values('poc__employee_name')[:1]),
                preferred_location=Subquery(marketing.values('preferred_location')[:1]),
                previous_marketing_days=Subquery(marketing.values('previous_marketing_days')[:1]),
            ).values('id', 'name', 'skills', 'preferred_location', 'recruiter', 'rtg', 'rate', 'in_pool',
                     'marketing_start', 'previous_marketing_days')
            return Response({"results": data, "count": count}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantMarketingViewSets(CreateModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantMarketing.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantMarketingSerializer

    def list(self, request, *args, **kwargs):
        try:
            close_marketing()
            start_marketing()
            marketing = ConsultantMarketing.objects.filter(
                consultant_id=request.query_params.get('consultant')
            )
            serializer = ConsultantMarketingCycleSerializer(marketing, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=request.data['consultant'])
            queryset = consultant.marketing.filter(status='close')
            if queryset:
                latest_marketing_cycle = queryset.latest('end')
            else:
                latest_marketing_cycle = None

            if consultant.status == 'terminated':
                consultant.status = 'on_bench'
                consultant.save()

            reset_days = request.data.get('reset_days', 'true')
            if reset_days == 'true':
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
                rtg=request.data['rtg'],
                in_pool=request.data['in_pool'],
                start=request.data['marketing_start'],
                consultant_id=request.data['consultant'],
                previous_marketing_days=previous_marketing_days,
                preferred_location=request.data['preferred_location'],
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
            return Response({"result": "Cycle Created"}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            consultant_marketing = get_object_or_404(ConsultantMarketing, id=kwargs.get('pk'))
            serializer = ConsultantMarketingCreateSerializer(consultant_marketing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='stop_marketing')
    def stop_marketing(self, request, *args, **kwargs):
        try:
            marketing = get_object_or_404(ConsultantMarketing, id=kwargs.get('pk'))
            marketing.end = request.data.get('end')
            marketing.save()
            close_marketing()
            return Response({"result": "marketing stopped"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='remarketing')
    def remarketing(self, request, *args, **kwargs):
        try:
            marketing = ConsultantMarketing.objects.filter(
                consultant_id=request.query_params.get('consultant')
            )
            serializer = ConsultantMarketingCycleSerializer(marketing, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='previous_marketing')
    def previous_marketing(self, request, *args, **kwargs):
        try:
            marketing = ConsultantMarketing.objects.filter(
                consultant_id=request.query_params.get('consultant')
            ).latest('end')
            serializer = ConsultantMarketingCycleSerializer(marketing)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Marketer assignment
    @action(methods=["put"], detail=True, url_path='marketer_assignment')
    def marketer_assignment(self, request, *args, **kwargs):
        try:
            queryset = ConsultantMarketing.objects.filter(id=kwargs.get('pk'))
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.teams.all()):
                marketer_ids = request.data.get('marketers', None)
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.add(marketer)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Team Assignment
    @action(methods=['put'], detail=True, url_path='team_assignment')
    def team_assignment(self, request, *args, **kwargs):
        try:
            queryset = ConsultantMarketing.objects.filter(id=kwargs.get('pk'))
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            if 'superadmin' in request.user.roles:
                team_ids = request.data.get('teams')
                for team_id in team_ids:
                    team = get_object_or_404(Team, id=team_id)
                    consultant_marketing.teams.add(team)
                serializer = TeamSerializer(consultant_marketing.teams.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Remove assigned Marketer from Consultant
    @action(methods=['put'], detail=True, url_path='remove_marketer')
    def remove_marketer(self, request, *args, **kwargs):
        try:
            queryset = ConsultantMarketing.objects.filter(id=kwargs.get('pk'))
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.teams.all()):
                marketer_ids = request.data.get('marketers', None)
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.remove(marketer)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Remove team from Consultant
    @action(methods=['put'], detail=True, url_path='remove_team')
    def remove_team(self, request, *args, **kwargs):
        try:
            queryset = ConsultantMarketing.objects.filter(id=kwargs.get('pk'))
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            if 'superadmin' in request.user.roles:
                team_ids = request.data.get('teams')
                for team_id in team_ids:
                    team = get_object_or_404(Team, id=team_id)
                    consultant_marketing.teams.remove(team)
                serializer = TeamSerializer(consultant_marketing.teams.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Return Consultant Profiles
    def list(self, request, *args, **kwargs):
        try:
            consultant_id = request.query_params.get('con_id', None)
            consultant = get_object_or_404(Consultant, id=consultant_id)
            profiles = consultant.profiles.all()
            serializer = self.serializer_class(profiles, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            suffix = data['title'].strip()
            name = request.user.employee_name
            initials = name.split()[0][0] + name.split()[1][0] if len(name.split()) > 1 else ""
            title = f'{initials.upper()}-{data["visa_type"]}-{data["dob"][:4]}-{suffix}'

            consultant_profile = ConsultantProfile.objects.create(
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
            serializer = self.serializer_class(consultant_profile)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            consultant_profile_id = kwargs.get('pk')
            consultant_profile = get_object_or_404(ConsultantProfile, id=consultant_profile_id)
            serializer = self.serializer_class(consultant_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            return Response({"error": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantPOCViewSets(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantPOC.objects.all()
    serializer_class = ConsultantPOCSerializer
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        try:
            instance = ConsultantPOC.objects.filter(poc_type=request.data['poc_type'],
                                                    consultant=request.data['consultant'],
                                                    end=None)
            if instance:
                previous_poc = instance.first()
                previous_poc.end = date.today()
                previous_poc.save()
            ConsultantPOC.objects.create(
                poc_id=request.data['poc'],
                poc_type=request.data['poc_type'],
                consultant_id=request.data['consultant'],
                start=date.today()
            )
            return Response({"result": "Created"}, status=status.HTTP_201_CREATED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        try:
            instance = get_object_or_404(ConsultantPOC, id=kwargs.get('pk'))
            serializer = self.serializer_class(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)


class WorkAuthViewSets(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = WorkAuth.objects.all()
    serializer_class = WorkAuthSerializer
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
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
            serializer = self.serializer_class(work_auth)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        try:
            instance = get_object_or_404(WorkAuth, id=kwargs.get('pk'))
            serializer = self.serializer_class(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantExitViewSets(RetrieveModelMixin, ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantExit.objects.all()
    serializer_class = ExitDetailConsultantSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        con_status = request.query_params.get('status', 'all')
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            consultants = Consultant.objects.filter(status='terminated')

            # Consultants search based on name, email, recruiter and location
            if query:
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

            # Filter Consultant by status
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
            return Response({"results": data, "count": count}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

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
                legal_action=request.data.get('legal_action', False),
                notice_period=request.data.get('notice_period', None),
            )

            reasons = request.data.get('reasons', [])
            for reason in reasons:
                reason = get_object_or_404(ExitReason, id=reason)
                con_exit.reasons.add(reason)

            if request.data.get('last_date', None) and request.data.get('last_date', None) <= str(date.today()):
                terminate_consultant(con_exit)

            # Mattermost message for exit interview
            if request.data.get('exit_details', None):
                send_exit_interview_detail(con_exit)

            # Email for starting Exit Process
            res = "Development Server"
            if os.environ.get('ENV', 'local') == 'prod':
                res, error = send_exit_process_mail(con_exit, 'start')
                if error == 'error':
                    logger.error(res)
                    return Response({"error": "error", "exit_mail_error": str(res)}, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.serializer_class(consultant.exit.all().order_by('-created'), many=True)
            return Response({"result": serializer.data, "exit_mail": str(res)}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

            con_exit = get_object_or_404(ConsultantExit, id=kwargs.get('pk'))
            serializer = ExitConsultantSerializer(con_exit, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if request.data.get('last_date', None) and request.data.get('last_date', None) <= str(date.today()):
                terminate_consultant(con_exit)

            # Mattermost message for exit interview
            if request.data.get('exit_details', None):
                send_exit_interview_detail(con_exit)
            serializer = self.serializer_class(con_exit)
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='cancel')
    def cancel_termination(self, request, *args, **kwargs):
        try:
            roles = request.user.roles
            if not ('superadmin' in roles or 'recruiter' in roles or 'retention' in roles):
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

            exit_id = kwargs.get('pk')
            con_exit = get_object_or_404(ConsultantExit, id=exit_id)

            if request.data.get('cancel_reason', None):
                if not con_exit.last_date or con_exit.last_date > date.today():
                    con_exit.status = 'cancelled'
                    con_exit.cancel_reason = request.data.get('cancel_reason')
                    con_exit.save()
                    # Email for Exit Process Cancelled
                    res = "Development Server"
                    if os.environ.get('ENV', 'local') == 'prod':
                        res, error = send_exit_process_mail(con_exit, 'cancel')
                        if error == 'error':
                            logger.error(res)
                            return Response({"error": "error", "exit_mail_error": str(res)},
                                            status=status.HTTP_400_BAD_REQUEST)
                    serializer = self.serializer_class(con_exit)
                    return Response({"result": serializer.data, "exit_mail": str(res)}, status=status.HTTP_202_ACCEPTED)
            return Response({"error": "Exit process can not be cancelled "}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='reason')
    def termination_reason(self, request):
        try:
            reasons = ExitReason.objects.all().values('id', 'name')
            return Response({'result': reasons}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class FeedbackViewSet(GenericViewSet, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin):
    queryset = Feedback.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantFeedbackSerializer

    def create(self, request, *args, **kwargs):
        try:
            feedback = Feedback.objects.create(
                created_by=request.user,
                rating=request.data.get('rating'),
                consultant_id=request.data.get('consultant'),
                feedback_type=request.data.get('feedback_type'),
                feedback_text=request.data.get('feedback_text'),
            )
            serializer = self.serializer_class(feedback)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            feedback_type = request.query_params.get('type', None)
            feedback = Feedback.objects.filter(consultant_id=kwargs.get('pk')).order_by('-created')
            if feedback_type:
                feedback = feedback.filter(feedback_type=feedback_type)
            serializer = self.serializer_class(feedback, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            feedback = get_object_or_404(Feedback, id=kwargs.get('pk'))
            serializer = self.serializer_class(feedback, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# API for Petition Web App
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
        email = request.data.get('email').lower()
        if email:
            consultant = get_object_or_404(Consultant, email=email)
        else:
            return Response({"error": "Email is Empty"}, status=status.HTTP_400_BAD_REQUEST)
        consultant = Consultant.objects.filter(email=consultant.email, pin=request.data.get('password').strip())
        if consultant:
            consultant = consultant.first()
            if not consultant.p_is_active:
                return Response({"error": "User account is not Active"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                serializer = self.serializer_class(consultant)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        logger.error("Incorrect Email Id OR Password")
        return Response({"error": "Incorrect Email Id OR Password"}, status=status.HTTP_400_BAD_REQUEST)

