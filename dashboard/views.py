from django.db.models import F, Q
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication


from project.models import Project
from consultant.models import Consultant
from log1.utils import ERROR_MSG, write_exception
from marketing.models import Submission, Interview, Test


class MarketingDashboardViewSet(GenericViewSet, ListModelMixin):
    queryset = Submission.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        team_name = request.GET.get("team", None)
        filter_for = request.GET.get("filter_for", None)
        result_count = request.GET.get("result_count", 5)
        filter_by_time = request.GET.get("filter_by", None)
        start_year = request.GET.get("start_year", None)
        end_year = request.GET.get("end_year", None)

        try:
            if filter_for == 'my':
                sub = Submission.objects.filter(created_by=request.user)
                interviews = Interview.objects.filter(
                    Q(supervisor=request.user) |
                    Q(submission__created_by=request.user)
                )
                consultant = Consultant.objects.filter(marketing__marketer=request.user)
                project_qs = Project.objects.filter(submission__created_by=request.user)

            elif filter_for == 'team':
                if not team_name:
                    team_name = request.user.team.name
                sub = Submission.objects.filter(created_by__team__name=team_name)
                consultant = Consultant.objects.filter(marketing__teams__name=team_name)
                interviews = Interview.objects.filter(submission__marketing_team__name=team_name)
                project_qs = Project.objects.filter(submission__marketing_team__name=team_name)

            else:
                sub = Submission.objects.all()
                project_qs = Project.objects.all()
                interviews = Interview.objects.all()
                consultant = Consultant.objects.all()

            upcoming_interviews = interviews.filter(
                status__in=['scheduled', 'rescheduled'], start_time__gte=datetime.today()
            ).order_by('start_time')[:result_count].annotate(
                client=F('submission__client'),
                job_title=F('submission__lead__job_title'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
                consultant_name=F('submission__consultant_marketing__consultant__name'),
            ).values('id', 'start_time', 'end_time', 'consultant_name', 'marketer_name', 'vendor', 'client',
                     'job_title')

            upcoming_joining = project_qs.filter(
                statuses__status='on_boarded', statuses__is_current=True
            ).order_by('-start_date')[:result_count].annotate(
                client=F('submission__client'),
                vendor=F('submission__lead__vendor_company__name'),
                consultant_name=F('consultant__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'start_date', 'consultant_name', 'marketer_name', 'vendor', 'client', 'is_remote')

            new_offers = project_qs.filter(
                statuses__is_current=True,
                start_date__gte=datetime.today(),
                statuses__status__in=['new', 'received', 'on_boarded'],
            ).order_by('-start_date')[:result_count].annotate(
                client=F('submission__client'),
                consultant_name=F('consultant__name'),
                vendor=F('submission__lead__vendor_company__name'),
                marketer_name=F('submission__created_by__employee_name'),
            ).values('id', 'start_date', 'consultant_name', 'marketer_name', 'vendor', 'client', 'is_remote')

            data = {
                "new_offers": new_offers,
                "joining": upcoming_joining,
                "interviews": upcoming_interviews
            }

            last = date.today().replace(day=1) - timedelta(days=1)
            if start_year and end_year:
                first = date(int(start_year), 1, 1)
                last = date(int(end_year), 1, 1)

            elif filter_by_time == 'last_month':
                first = last.replace(day=1)

            elif filter_by_time == 'this_year':
                first = last.replace(day=1) + relativedelta(months=-(last.month-1))

            elif filter_by_time == 'last_6_month':
                first = last + timedelta(days=1) + relativedelta(months=-6)

            elif filter_by_time == 'last_12_month':
                first = last + timedelta(days=1) + relativedelta(months=-12)

            # this_month
            else:
                first = date.today().replace(day=1)
                last = date.today()
            projects = project_qs.filter(
                statuses__created__range=[first, last], submission__marketing_team__dept="Marketing"
            ).order_by('id').distinct('id').all()
            total = projects.count()
            new = projects.filter(statuses__status='new', statuses__is_current=True).count()
            joined = projects.filter(statuses__status='joined', statuses__is_current=True).count()
            received = projects.filter(statuses__status='received', statuses__is_current=True).count()
            on_boarded = projects.filter(statuses__status='on_boarded', statuses__is_current=True).count()
            extended = projects.filter(statuses__status__istartswith='extended', statuses__is_current=True).count()
            complete = projects.filter(statuses__status__istartswith='complete', statuses__is_current=True).count()
            cancelled = projects.filter(statuses__status__istartswith='cancelled', statuses__is_current=True).count()
            terminated = projects.filter(statuses__status__istartswith='terminate', statuses__is_current=True).count()
            not_joined = projects.filter(
                statuses__status='on_boarded', statuses__is_current=True, start_date__lt=date.today()).count()

            count = {
                'total_offers': total,
                'offer': project_qs.filter(created__range=[first, last], submission__marketing_team__dept="Marketing").count(),
                'submission': sub.filter( created__range=[first, last], marketing_team__dept="Marketing")
                    .exclude(status='draft').count(),
                'on_project': consultant.filter(status='on_project', created__range=[first, last]).count(),
                'ba_bench': consultant.filter(skills__contains='BA', status='on_bench', created__range=[first, last]).count(),
                'dev_bench':  consultant.filter(status='on_bench', created__range=[first, last]).exclude(skills__exact='BA').count(),
                'interview': interviews.filter(
                    created__range=[first, last], submission__marketing_team__dept="Marketing"
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            }

            offer_count = [
                {'name': 'new', 'count': new},
                {'name': 'joined', 'count': joined},
                {'name': 'received', 'count': received},
                {'name': 'extended', 'count': extended},
                {'name': 'complete', 'count': complete},
                {'name': 'cancelled', 'count': cancelled},
                {'name': 'terminated', 'count': terminated},
                {'name': 'on_boarded', 'count': on_boarded},
                {'name': 'not_joined', 'count': not_joined},
            ]
            return Response({'data': data, 'count': count, 'offer_count': offer_count}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)

    @action(methods=['get'], detail=False, url_path='performance')
    def marketing_performance(self, request):
        team_name = request.GET.get("team", None)
        filter_for = request.GET.get("filter_for", None)
        filter_by_time = request.GET.get("filter_by", None)
        start_year = request.GET.get("start_year", None)
        end_year = request.GET.get("end_year", None)

        try:
            last = date.today().replace(day=1) - timedelta(days=1)
            if start_year and end_year:
                first = date(int(start_year), 1, 1)
                last = date(int(end_year), 1, 1)
                prev_last = last + timedelta(days=(last - first).days)
                prev_first = first + timedelta(days=(last - first).days)

            elif filter_by_time == 'last_month':
                first = last.replace(day=1)

                prev_last = last + relativedelta(months=-1)
                prev_first = first + relativedelta(months=-1)

            elif filter_by_time == 'last_6_month':
                first = last + timedelta(days=1) + relativedelta(months=-6)

                prev_last = last + relativedelta(months=-6)
                prev_first = first + relativedelta(months=-6)

            elif filter_by_time == 'last_12_month':
                first = last + timedelta(days=1) + relativedelta(months=-12)

                prev_last = last + relativedelta(months=-12)
                prev_first = first + relativedelta(months=-12)

            # this_month
            else:
                last = date.today()
                prev_first, prev_last = None, None
                first = date.today().replace(day=1)

            if filter_for == 'my':
                new_po = Project.objects.filter(
                    statuses__status='joined',
                    submission__created_by=request.user,
                    statuses__created__range=[first, last],
                ).count()

                offers_count = Project.objects.filter(
                    submission__created__range=[first, last], submission__created_by=request.user
                ).count()

                submissions_count = Submission.objects.filter(
                    created__range=[first, last], created_by=request.user
                ).count()

                interviews_count = Interview.objects.filter(
                    submission__created_by=request.user,
                    submission__created__range=[first, last],
                    status__in=['offer', 'failed', 'feedback_due'],
                ).count()

                joining_count = Project.objects.filter(
                    statuses__status='joined',
                    submission__created_by=request.user,
                    submission__created__range=[first, last],
                ).count()

            elif filter_for == 'team':
                if not team_name:
                    team_name = request.user.team.name

                new_po = Project.objects.filter(
                    statuses__status='joined',
                    statuses__created__range=[first, last],
                    submission__marketing_team__name=team_name,
                ).count()

                offers_count = Project.objects.filter(
                    submission__created__range=[first, last], submission__marketing_team__name=team_name
                ).count()

                submissions_count = Submission.objects.filter(
                    created__range=[first, last], created_by__team__name=team_name
                ).count()

                interviews_count = Interview.objects.filter(
                    submission__created__range=[first, last],
                    submission__marketing_team__name=team_name,
                    status__in=['offer', 'failed', 'feedback_due'],
                ).count()

                joining_count = Project.objects.filter(
                    statuses__status='joined',
                    submission__created__range=[first, last],
                    submission__marketing_team__name=team_name
                ).count()

            else:
                submissions_count = Submission.objects.filter(created__range=[first, last]).count()
                offers_count = Project.objects.filter(submission__created__range=[first, last]).count()
                interviews_count = Interview.objects.filter(
                    submission__created__range=[first, last], status__in=['offer', 'failed', 'feedback_due']
                ).count()
                new_po = Project.objects.filter(
                    statuses__status='joined', statuses__created__range=[first, last]
                ).count()
                joining_count = Project.objects.filter(
                    statuses__status='joined', submission__created__range=[first, last]
                ).count()

            percent = None
            if filter_by_time != 'this_month':
                prev_po = Project.objects.filter(
                    statuses__status='joined', created__range=[prev_first, prev_last]
                ).count()

                if prev_po != 0:
                    percent = int(((new_po - prev_po) / prev_po) * 100)

            conversions = {
                "offers": 0,
                "joining": 0,
                "interview": 0,
                "count": {
                    "offer_count": offers_count,
                    "joining_count": joining_count,
                    "interview_count": interviews_count,
                    "submission_count": submissions_count,
                }
            }
            if submissions_count != 0:
                conversions['offers'] = round((offers_count / submissions_count) * 100, 2)
                conversions['joining'] = round((joining_count / submissions_count) * 100, 2)
                conversions['interview'] = round((interviews_count / submissions_count) * 100, 2)

            result = {
                "joined_count": new_po,
                "joined_percent": percent,
                "conversions": conversions
            }
            return Response({"data": result}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)

    @action(methods=['get'], detail=False, url_path='history')
    def dashboard_history(self, request):
        team_name = request.GET.get("team", None)
        filter_for = request.GET.get("filter_for", "")
        filter_by_time = request.GET.get("filter_by", "")
        start_year = request.GET.get("start_year", None)
        end_year = request.GET.get("end_year", None)

        try:
            if filter_for == 'my':
                projects = Project.objects.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                if not team_name:
                    team_name = request.user.team.name
                projects = Project.objects.filter(submission__marketing_team__name=team_name)
            else:
                projects = Project.objects.all()

            result = []
            diff = 0
            if filter_by_time == 'last_12_month':
                diff = 12

            elif filter_by_time == 'last_6_month':
                diff = 6

            last = date.today().replace(day=1) - timedelta(days=1) + relativedelta(months=-(diff - 1))
            first = last.replace(day=1)

            if start_year and end_year:
                first = date(int(start_year), 1, 1)
                last = date(int(end_year), 1, 1)
                diff = (relativedelta(last, first)).years*12
            for i in range(diff):
                projects_count = projects.filter(created__range=[first, last]).count()
                data = {
                    "month": first.strftime('%b'),
                    "po": projects_count
                }
                result.append(data)
                first = first + relativedelta(months=1)
                last = last.replace(day=1) + relativedelta(months=2) - timedelta(days=1)
            return Response({"data": result}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)

    @action(methods=['get'], detail=False, url_path='pending_status')
    def pending_status(self, request):
        try:
            team_name = request.GET.get("team", None)
            filter_for = request.GET.get("filter_for", "")

            today = date.today() - timedelta(days=7)
            tests = Test.objects.filter(status='feedback_due', submit_date__lte=today)
            interviews = Interview.objects.filter(status='feedback_due', start_time__date__lte=today)

            if filter_for == 'my':
                tests = tests.filter(submission__created=request.user)
                interviews = interviews.filter(submission__created_by=request.user)
            elif filter_for == 'team':
                if not team_name:
                    team_name = request.user.team.name
                tests = tests.filter(submission__created__team__name=team_name)
                interviews = interviews.filter(submission__marketing_team__name=team_name)
            data = {
                "interviews": interviews.annotate(
                    marketer=F('submission__created_by__employee_name')
                ).values('id', 'marketer', 'start_time'),
                "tests": tests.annotate(
                    marketer=F('submission__created_by__employee_name')
                ).values('id', 'marketer', 'submit_date'),
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)
