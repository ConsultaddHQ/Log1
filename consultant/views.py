import logging
from datetime import date, datetime
from django.shortcuts import get_object_or_404
from django.db.models import Subquery, OuterRef, Q, Count

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin

from project.models import Project
from consultant.serializers import *
from marketing.models import Submission, Interview
from attachment.serializers import AttachmentURLSerializer
from activity.serializers import CommentGetSerializer

logger = logging.getLogger(__name__)
dont_have_access = 'you don\'t have access'


class ConsultantViewSets(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
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
            data = queryset[first:last].annotate(
                rate=F('submission__rate'),
                client=F('submission__client'),
                consultant_name=F('consultant__name'),
                company_name=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name')
            ).values('id', 'consultant_name', 'city', 'company_name', 'client', 'rate', 'marketer_name', 'created')
            return data, data_counts
        except Exception as error:
            logger.error(error)
            return error, 'error'

    def list(self, request, *args, **kwargs):
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

        consultants = consultants.order_by('id').distinct('id')
        serializer = ConsultantListSerializer(consultants, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        try:
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
        if not ('superadmin' in roles or 'recruiter' in roles):
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
                skype=data['skype'],
                links=data['links'],
                skills=data['skills'],
                gender=data['gender'],
                date_of_birth=data['dob'],
                phone_no=data['phone_no'],
                work_type=data['work_type'],
                current_city=data['current_city'],

            )

            # Creating Consultant Original Profile Consultant
            ConsultantProfile.objects.create(
                title="Original",
                links=data['links'],
                consultant=consultant,
                date_of_birth=data['dob'],
                visa_end=data['visa_end'],
                profile_owner=request.user,
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
                current_city=data['current_city'],
            )

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
                visa_type=data['visa_type'],
                visa_start=data['visa_start'],
            )

        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"result": ConsultantSerializer(consultant).data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
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

    @action(methods=['post', 'put'], detail=True, url_path='education')
    def education(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'POST':
            try:
                data = request.data
                Education.objects.create(
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
                return Response({"result": "created"}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                education = get_object_or_404(Education, id=kwargs.get('pk'))
                serializer = EducationSerializer(education, data=request.data, partial=True)
                return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post', 'put'], detail=True, url_path='experience')
    def experience(self, request, *args, **kwargs):
        roles = request.user.roles
        if not ('superadmin' in roles or 'recruiter' in roles):
            return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'POST':
            try:
                data = request.data
                Experience.objects.create(
                    city=data['city'],
                    title=data['title'],
                    remark=data['remark'],
                    company=data['company'],
                    exp_type=data['exp_type'],
                    end_date=data['end_date'],
                    start_date=data['start_date'],
                    consultant_id=kwargs.get('pk'),
                )
                return Response({"result": "created"}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                experience = get_object_or_404(Experience, id=kwargs.get('pk'))
                serializer = ExperienceSerializer(experience, data=request.data, partial=True)
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
                    submission__consultant_marketing__status='open',
                    submission__consultant_marketing__end=None,
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
                feedback_type = request.query_params.get("feedback_type", None)
                if feedback_type:
                    queryset = ConsultantFeedback.objects.filter(
                        consultant_id=consultant_id, feedback_type=feedback_type
                    )
                else:
                    queryset = ConsultantFeedback.objects.filter(consultant_id=consultant_id)
                serializer = ConsultantFeedbackSerializer(queryset[first:last], many=True)
                return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'POST':
            try:
                consultant_id = kwargs.get('pk')
                data = request.data
                feedback_details = FeedbackDetail.objects.create(
                    role_knowledge=data['role'],
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
        consultant_id = kwargs.get('pk')
        if request.method == 'GET':
            try:
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
                comment = Comment.objects.create(
                    user=request.user,
                    object_id=consultant_id,
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
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk'))
            queryset = consultant.attachments.all()
            serializer = AttachmentURLSerializer(queryset, many=True)
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
            marketing__status='open', marketing__is_current=True
        ).values('current_city').annotate(total=Count('current_city')).order_by('current_city')
        return Response({"results": consultants}, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        team_name = request.query_params.get('team', None)
        location = request.query_params.get('location', None)
        con_status = request.query_params.get('status', 'in_marketing')
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

        try:
            consultants = Consultant.objects.filter(
                Q(marketing__status='open')
            )
            # Team wise Filter
            if team_name and team_name != 'all' and team_name.lower() != 'consultadd':
                consultants = consultants.filter(marketing__teams__name=team_name)

            # Location wise Filter
            if location:
                con_status = 'in_marketing'
                consultants = consultants.filter(
                    current_city=location,
                    marketing__status='open',
                )

            # Consultants search based on name, email, recruiter and location
            elif query:
                consultants = consultants.filter(
                    Q(name__icontains=query) | Q(email__iexact=query) | Q(skills__icontains=query) |
                    Q(current_city__icontains=query) | Q(pocs__poc__employee_name__istartswith=query, pocs__end=None)
                )

            consultants = consultants.order_by('id').distinct('id')
            in_pool = consultants.filter(marketing__status='open', status='on_bench', marketing__in_pool=True).count()
            on_bench = consultants.filter(marketing__status='open', status='on_bench', marketing__in_pool=False).count()
            on_project = consultants.filter(status='on_project').count()

            count = {
                "in_pool": in_pool,
                "on_bench": on_bench,
                "on_project": on_project,
                "total": in_pool + on_bench + on_project,
            }

            # Filter Consultant by status and In pool
            if con_status == 'in_pool':
                consultants = consultants.filter(marketing__status='open', marketing__in_pool=True)
            else:
                consultants = consultants.filter(status=con_status, marketing__status='open', marketing__in_pool=False)
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
            ).values('id', 'name', 'skills', 'preferred_location', 'recruiter', 'rtg', 'rate', 'in_pool',
                     'marketing_start')
            return Response({"results": data, "count": count}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantMarketingViewSets(UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConsultantMarketing.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ConsultantMarketingSerializer

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

    @action(methods=['get', 'post'], detail=False, url_path='remarketing')
    def remarketing(self, request, *args, **kwargs):
        if request.method == 'GET':
            try:
                marketing = ConsultantMarketing.objects.filter(consultant_id=request.query_params.get('consultant'),
                                                               status='open')
                data = marketing.values('id', 'start', 'end', 'rtg', 'in_pool', 'cycle', 'preferred_location',
                                        'status', 'primary_marketer__employee_name', 'primary_marketer__team__name')
                return Response({"result": data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                prev_marketing_obj = ConsultantMarketing.objects.filter(consultant_id=request.data['consultant'],
                                                                        status='open')
                cycle = 1
                if prev_marketing_obj:
                    cycle = prev_marketing_obj.first().cycle + 1

                consultant_marketing = ConsultantMarketing.objects.create(
                    cycle=cycle,
                    rtg=request.data['rtg'],
                    in_pool=request.data['in_pool'],
                    start=request.data['marketing_start'],
                    consultant_id=request.data['consultant'],
                    primary_marketer_id=request.data['primary_marketer'],
                    preferred_location=request.data['preferred_location'],
                )

                teams = request.data.get('teams', [])
                for team in teams:
                    consultant_marketing.teams.add(get_object_or_404(Team, name=team))

                marketer_ids = request.data.get('marketers', [])
                for marketer_id in marketer_ids:
                    marketer = get_object_or_404(User, id=marketer_id)
                    consultant_marketing.marketer.add(marketer)

            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Marketer assignment
    @action(methods=["put"], detail=True, url_path='marketer_assignment')
    def marketer_assignment(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, status='open')
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
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Team Assignment
    @action(methods=['put'], detail=True, url_path='team_assignment')
    def team_assignment(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, status='open')
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
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, status='open')
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
                return Response({"result": dont_have_access}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    # Remove team from Consultant
    @action(methods=['put'], detail=True, url_path='remove_team')
    def remove_team(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            queryset = ConsultantMarketing.objects.filter(consultant_id=consultant_id, status='open')
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

    def destroy(self, request, *args, **kwargs):
        try:
            consultant_profile_id = kwargs.get('pk')
            consultant_profile = get_object_or_404(ConsultantProfile, id=consultant_profile_id)
            consultant_profile.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
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
        if not ('superadmin' in roles or 'recruiter' in roles):
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
        if not ('superadmin' in roles or 'recruiter' in roles):
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
        if not ('superadmin' in roles or 'recruiter' in roles):
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
        if not ('superadmin' in roles or 'recruiter' in roles):
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
