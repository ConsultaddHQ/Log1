import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Subquery, OuterRef, Q, F, Count

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets, exceptions
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin

from project.models import Project
from consultant.serializers import *
from marketing.models import Submission, Interview
from consultant.auth import consultant_authenticate
from attachment.serializers import AttachmentSerializer
from consultant.permissions import ConsultantIsAuthenticated
from employee.models import get_password_reset_token_expiry_time
from activity.serializers import CommentSerializer, CommentGetSerializer
from employee.serializers import PasswordTokenSerializer, EmailSerializer
from consultant.authentication import ConsultantTokenAuthentication, get_consultant

logger = logging.getLogger(__name__)


# API for Mobile App
class ConsultantAuthViewSets(GenericViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer

    @action(methods=['post'], detail=False, url_path='register')
    def register(self, request):
        """
            User Register
            :param request, email, password, employee_id, name, phone, gender, team, role
        """
        try:
            email = request.data.get('email')
            password = request.data.get('password').strip()

            queryset = Consultant.objects.filter(email__exact=email)
            if queryset:
                consultant = queryset.first()
                consultant.set_password(password)
                consultant.is_active = True
                consultant.save()

                return Response({"result": "Success"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Consultant Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
        """
        email = request.data.get('email')
        if email:
            consultant = get_object_or_404(Consultant, email=email)
        else:
            return Response({"error": "Email is Empty"}, status=status.HTTP_400_BAD_REQUEST)
        consultant = consultant_authenticate(email=consultant.email, password=request.data.get('password').strip())
        if consultant:
            return Response({"result": self.serializer_class(consultant).data}, status=status.HTTP_202_ACCEPTED)
        logger.error("Incorrect Email Id OR Password")
        return Response({"error": "Incorrect Email Id OR Password"}, status=status.HTTP_400_BAD_REQUEST)


# API for Mobile App
class ConsultantAppViewSets(ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        queryset = Consultant.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        consultant = get_consultant(request)
        if consultant.check_password(current_password):
            consultant.set_password(new_password)
            consultant.save()
            return Response({"result": "password updated"}, status=status.HTTP_200_OK)
        return Response({"error": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['delete'], detail=False, url_path='logout')
    def logout(self, request):
        """
            Logout for authenticated user
        """
        token = get_object_or_404(ConsultantToken, key=request.auth)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# API for Mobile App
class ConsultantResetPasswordViewSets(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
    serializer_class = EmailSerializer
    pass_serializer_class = PasswordTokenSerializer

    @action(methods=['post'], detail=False, url_path='token_request')
    def token_request(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        clear_expired(now_minus_expiry_time)

        consultants = Consultant.objects.filter(email__iexact=email)

        active_user_found = False
        for consultant in consultants:
            if consultant.is_active and consultant.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            logger.info("User is not active")
            raise exceptions.ValidationError({
                'email': [
                    "There is no active user associated with this e-mail address or the password can not be changed"],
            })
        ip = request.META['REMOTE_ADDR']
        for consultant in consultants:
            if consultant.is_active and consultant.has_usable_password():
                if consultant.password_reset_tokens.all().count() > 0:
                    token = consultant.password_reset_tokens.all()[0]
                else:
                    token = ConsultantResetPasswordToken.objects.create(
                        consultant=consultant,
                        user_agent=request.META['HTTP_USER_AGENT'],
                        ip_address=ip if ip else '127.0.0.1'
                    )
                mail_data = {
                    'to': [consultant.email],
                    'cc': [],
                    'bcc': [],
                    'subject': 'Reset Log1 Password',
                    'template': '../templates/password_reset.html',
                    'context': {
                        'name': consultant.name,
                        'email': consultant.email,
                        'token': token,
                    },
                }
                res, error = consultant.send_mail(mail_data)
                if error == 'error':
                    logger.error(res)
                    return Response({'error': str(res)}, status=status.HTTP_200_OK)
        return Response({'status': 'OK'}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        reset_password_token = ConsultantResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({'status': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

        if timezone.now() > expiry_date:
            reset_password_token.delete()
            return Response({'status': 'expired'}, status=status.HTTP_404_NOT_FOUND)

        reset_password_token.consultant.set_password(password)
        reset_password_token.consultant.save()

        # Delete all password reset tokens for this user
        ConsultantResetPasswordToken.objects.filter(consultant=reset_password_token.consultant).delete()

        return Response({'status': 'OK'}, status=status.HTTP_200_OK)


class ConsultantViewSets(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
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
                marketer_name=F('lead__marketer__employee_name'),
                location=F('lead__city')
            ).values('id', 'rate', 'consultant_name', 'company_name', 'marketer_name', 'location', 'project')

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
                ctb_name=F('supervisor__employee_name'),
                client=F('submission__client'),
                project=F('submission__project'),
                marketer_name=F('submission__lead__marketer__employee_name'),
                company_name=F('submission__lead__vendor_company__name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),

            ).values('id', 'round', 'status', 'start_time', 'end_time', 'interview_type', 'submission_id',
                     'supervisor__employee_name', 'marketer_name', 'consultant_name', 'client', 'company_name',
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
            new = queryset.filter(status='new').count()
            joined = queryset.filter(status='joined').count()
            received = queryset.filter(status='received').count()
            on_boarded = queryset.filter(status='on_boarded').count()
            not_joined = queryset.filter(status='not_joined').count()

            queryset = queryset.order_by('-modified').distinct('modified')
            if filter_by_status:
                queryset = queryset.filter(status=filter_by_status)

            data_counts = {
                'new': new,
                'total': total,
                'joined': joined,
                'received': received,
                'on_boarded': on_boarded,
                'not_joined': not_joined,
            }
            data = queryset[first:last].annotate(
                consultant_name=F('consultant__name'),
                location=F('submission__lead__city'),
                company_name=F('submission__lead__vendor_company__name'),
                client=F('submission__client'),
                rate=F('submission__rate'),
                marketer_name=F('submission__lead__marketer__employee_name')
            ).values('id', 'consultant_name', 'location', 'company_name', 'client', 'rate', 'marketer_name')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    def list(self, request, *args, **kwargs):
        consultants = Consultant.objects.filter(status='in_marketing')
        roles = request.user.roles

        if 'marketer' in request.user.roles:
            consultants = consultants.filter(
                Q(in_pool=True) |
                Q(marketer=request.user)
            )
        elif 'admin' in roles or 'proxy' in roles:
            consultants = consultants.filter(
                Q(teams=request.user.team, in_pool=False) |
                Q(in_pool=True)
            )

        elif 'recruiter' in roles:
            consultants = consultants.filter(
                pocs__poc=request.user
            )

        consultants = consultants.order_by('id').distinct('id')
        serializer = ConsultantListSerializer(consultants, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            consultant = get_object_or_404(Consultant, id=consultant_id)
            serializer = self.serializer_class(consultant)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles and 'recruiter' in roles):
            return Response({"error": "you don't have access"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        consultant = Consultant.objects.filter(email__iexact=data['email'])
        if consultant:
            return Response({"result": "Consultant Already Exist"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.create(
                ssn=data['ssn'],
                name=data['name'],
                email=data['email'],
                skype=data['skype'],
                links=data['links'],
                skills=data['skills'],
                gender=data['gender'],
                date_of_birth=data['dob'],
                phone_no=data['phone_no'],
                work_type=data['work_type'],
                current_city=data['current_city'],
            )

            # Creating Marketing Cycle of Consultant
            consultant_marketing = ConsultantMarketing.objects.create(
                consultant=consultant,
                in_pool=data['in_pool'],
                start=data['marketing_start'],
                primary_marketer_id=data['primary_marketer'],
                preferred_location=data['preferred_location'],
            )

            teams = request.data.get('teams', None)
            if teams:
                for team in teams:
                    consultant_marketing.teams.add(get_object_or_404(Team, name=team))

            # Creating Recruiter of Consultant
            ConsultantPOC.objects.create(
                consultant=consultant,
                poc_type='recruiter',
                start=timezone.now(),
                poc_id=data['recruiter']
            )

            # Creating Retention of Consultant
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
                visa_start=data['visa_start'],
                visa_type=data['visa_type'],
            )

        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"result": "Created"}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
            return Response({"error": "you don't have access"}, status=status.HTTP_403_FORBIDDEN)
        obj_id = kwargs.get('pk')
        con_obj = request.query_params.get('type')
        obj_status = request.query_params.get('obj_status')
        con_classes = {
            'work_auth': WorkAuth,
            'consultant': Consultant,
            'relation': ConsultantPOC,
            'recruiter': ConsultantPOC,
            'marketing': ConsultantMarketing,
            'education': EducationSerializer,
            'experience': ExperienceSerializer,
            'rate_revision': ConsultantRateRevisionSerializer,
            'serializer': {
                'work_auth': WorkAuthSerializer,
                'education': EducationSerializer,
                'experience': ExperienceSerializer,
                'relation': ConsultantPOCSerializer,
                'recruiter': ConsultantPOCSerializer,
                'consultant': ConsultantUpdateSerializer,
                'marketing': ConsultantMarketingCreateSerializer,
                'rate_revision': ConsultantRateRevisionSerializer,
            }
        }
        try:
            if obj_status == 'create':
                serializer = con_classes['serializer'][con_obj](data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({"result": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                obj = get_object_or_404(con_classes[con_obj], id=obj_id)
                serializer = con_classes['serializer'][con_obj](obj, data=request.data, partial=True)
                serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except KeyError as err:
            logger.error(err)
            return Response({"error": "%s Object type not found" % (con_obj,)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True, url_path='education')
    def education(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
            return Response({"error": "you don't have access"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        consultant_id = kwargs.get('pk')
        try:
            consultant = get_object_or_404(Consultant, id=consultant_id)

            Education.objects.create(
                city=data['city'],
                title=data['title'],
                major=data['major'],
                remark=data['remark'],
                consultant=consultant,
                org_name=data['org_name'],
                edu_type=data['edu_type'],
                end_date=data['end_date'],
                start_date=data['start_date'],
            )
            return Response({"result": "created"}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True, url_path='experience')
    def experience(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
            return Response({"error": "you don't have access"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        consultant_id = kwargs.get('pk')
        try:
            consultant = get_object_or_404(Consultant, id=consultant_id)
            Experience.objects.create(
                city=data['city'],
                title=data['title'],
                remark=data['remark'],
                consultant=consultant,
                company=data['company'],
                exp_type=data['exp_type'],
                end_date=data['end_date'],
                start_date=data['start_date'],
            )
            return Response({"result": "created"}, status=status.HTTP_201_CREATED)
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
            if marketing_stage == 'submission':
                submissions = Submission.objects.filter(
                    consultant_marketing__consultant_id=consultant_id,
                    consultant_marketing__end=None
                ).exclude(status='draft')
                data, counts = self.get_submission_data(submissions, filter_by_status, first, last)
                if counts == "error":
                    return Response({"error": str(data)}, status=status.HTTP_400_BAD_REQUEST)
            elif marketing_stage == 'interview':
                interviews = Interview.objects.filter(
                    submission__consultant_marketing__consultant_id=consultant_id,
                    submission__consultant_marketing__end=None
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
            return Response({"results": data, "data_count": counts})
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get', 'post'], detail=True, url_path='feedback')
    def feedback(self, request, *args, **kwargs):
        if request.method == 'GET':
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size
            try:
                consultant_id = kwargs.get('pk')
                feedback_type = request.query_params.get("feedback_type")
                queryset = ConsultantFeedback.objects.filter(consultant_id=consultant_id, feedback_type=feedback_type)
                serializer = CommentSerializer(queryset[first:last], many=True)
                return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'POST':
            try:
                consultant_id = kwargs.get('pk')
                data = request.data
                feedback_details = FeedbackDetail.objects.create(
                    role=data['role'],
                    experience=data['experience'],
                    programming=data['programming'],
                    communication=data['communication'],
                    organizational=data['organizational'],
                    problem_solving=data['problem_solving'],
                )
                feedback = ConsultantFeedback.objects.create(
                    remark=data['remark'],
                    rating=data['rating'],
                    created_by=request.user,
                    feedback=feedback_details,
                    consultant_id=consultant_id,
                    given_by_id=data['given_by'],
                    feedback_type=data['feedback_type'],
                )
                serializer = ConsultantFeedbackSerializer(feedback)
                return Response({'result': serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": 'Method not allowed'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get', 'post'], detail=True, url_path='comments')
    def comments(self, request, *args, **kwargs):
        if request.method == 'GET':
            try:
                consultant_id = kwargs.get('pk')
                consultant = get_object_or_404(Consultant, id=consultant_id)
                queryset = consultant.comments.filter(parent_comment=None)
                serializer = CommentGetSerializer(queryset, many=True)
                return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'POST':
            try:
                content_type = ContentType.objects.get(model='consultant')
                object_id = kwargs.get('pk', None)
                comment = Comment.objects.create(
                    user=request.user,
                    object_id=object_id,
                    content_type=content_type,
                    comment_text=request.data['comment_text'],
                    parent_comment_id=request.data['parent_comment'],
                )
                serializer = CommentGetSerializer(comment)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='documents')
    def documents(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            consultant = get_object_or_404(Consultant, id=consultant_id)
            queryset = consultant.attachments.all()
            serializer = AttachmentSerializer(queryset, many=True)
            return Response({'results': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='rate_revision')
    def rate_revision(self, request, *args, **kwargs):
        consultant_id = kwargs.get('pk')
        rate_revision = ConsultantRateRevision.objects.filter(consultant=consultant_id)
        data = rate_revision.values('id', 'rate', 'start', 'end', 'previous_rate', 'feedback')
        return Response({"results": data}, status=status.HTTP_200_OK)


class ConsultantBenchViewSets(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ConsultantBenchSerializer
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='map')
    def map(self, request):
        consultants = Consultant.objects.filter(status='in_marketing').values('current_city').annotate(
            total=Count('current_city')).order_by('current_city')
        return Response({"results": consultants}, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        team_name = request.query_params.get('team', None)
        con_status = request.query_params.get('status', 'in_marketing')
        query = request.query_params.get('query', None)
        location = request.query_params.get('location', None)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            consultants = Consultant.objects.filter(marketing__end=None).exclude(
                status__in=['new', 'archived', 'in_training', 'terminated'])
            # Team wise Filter
            if team_name:
                team = get_object_or_404(Team, name=team_name)
                consultants = consultants.filter(marketing__teams=team)

            # Location wise Filter
            if location:
                con_status = 'in_marketing'
                consultants = consultants.filter(current_city=location, status='in_marketing')

            # Consultants search based on name, email, recruiter and location
            elif query:
                consultants = consultants.filter(
                    Q(name__icontains=query) | Q(email__iexact=query) | Q(skills__icontains=query) |
                    Q(current_city__icontains=query) | Q(pocs__poc__employee_name__istartswith=query, pocs__end=None)
                )
                # Marketer's team Consultants
            else:
                consultants = consultants.filter(
                    Q(marketing__teams=request.user.team, marketing__in_pool=False) |
                    Q(marketing__marketer=request.user)
                )
            consultants = consultants.order_by('id').distinct('id')
            in_pool = consultants.filter(status='in_marketing', marketing__in_pool=True).count()
            in_marketing = consultants.filter(status='in_marketing', marketing__in_pool=False).count()

            count = {
                "total": in_pool + in_marketing,
                "in_pool": in_pool,
                "in_marketing": in_marketing
            }

            # Filter Consultant by status and In pool
            if con_status == 'in_pool':
                consultants = consultants.filter(status='in_marketing', marketing__in_pool=True)
            else:
                consultants = consultants.filter(status=con_status, marketing__in_pool=False)

            poc = ConsultantPOC.objects.filter(
                consultant=OuterRef("pk"), end=None, poc_type='recruiter')

            rate = ConsultantRateRevision.objects.filter(
                consultant=OuterRef("pk"), end=None)

            marketing = ConsultantMarketing.objects.filter(
                consultant=OuterRef("pk"), end=None)

            data = consultants[first:last].annotate(
                rate=Subquery(rate.values('rate')[:1]),
                rtg=Subquery(marketing.values('rtg')[:1]),
                in_pool=Subquery(marketing.values('in_pool')[:1]),
                marketing_start=Subquery(marketing.values('start')[:1]),
                recruiter=Subquery(poc.values('poc__employee_name')[:1]),
                preferred_location=Subquery(marketing.values('preferred_location')[:1]),
            ).values('id', 'name', 'skills', 'preferred_location', 'recruiter', 'rtg', 'rate', 'in_pool',
                     'marketing_start')

            return Response({"results": data, "count": count}, status=status.HTTP_200_OK)

        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantMarketingViewSets(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantMarketing.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantMarketingSerializer

    # Marketer assignment
    @action(methods=["put"], detail=True, url_path='marketer_assignment')
    def marketer_assignment(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, end=None)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.consultant.teams.all()):
                marketer_ids = request.data.get('marketers', None)
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.add(marketer)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_200_OK)

    # Team Assignment
    @action(methods=['put'], detail=True, url_path='team_assignment')
    def team_assignment(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, end=None)
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
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_200_OK)

    # Remove assigned Marketer from Consultant
    @action(methods=['put'], detail=True, url_path='remove_marketer')
    def remove_marketer(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, end=None)
            if queryset:
                consultant_marketing = queryset.first()
            else:
                return Response({"result": "Consultant is not in Marketing"})
            roles = request.user.roles
            if 'superadmin' in roles or (('admin' in roles or 'proxy' in roles) and request.user.team
                                         in consultant_marketing.consultant.teams.all()):
                marketer_ids = request.data.get('marketers', None)
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.remove(marketer)
                serializer = POCSerializer(consultant_marketing.marketer.all(), many=True)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Remove team from Consultant
    @action(methods=['put'], detail=True, url_path='remove_team')
    def remove_team(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, end=None)
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
                return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_200_OK)


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
            title = "{}-{}-{}".format(initials.upper(), data['visa_type'], data["dob"][:4])

            consultant_profile = ConsultantProfile.objects.create(
                links=data['links'],
                linkedin=data['linkedin'],
                date_of_birth=data['dob'],
                visa_end=data['visa_end'],
                title=title + "-" + suffix,
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

    def destroy(self, request, *args, **kwargs):
        try:
            consultant_profile_id = kwargs.get('pk')
            consultant_profile = get_object_or_404(ConsultantProfile, id=consultant_profile_id)
            consultant_profile.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
