from django.db.models import Q
from datetime import timedelta, date, datetime
from django.core.management import BaseCommand
from pytz import timezone

from employee.models import User
from marketing.models import Interview
from project.models import ProjectSupport
from notification.models import UserNotification
from django.contrib.auth.models import ContentType
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command send the push notification to project support person " \
           "if project updates are pending form last 7 days "

    @staticmethod
    def update_notification(queryset, content_type):
        content_type_obj = ContentType.objects.get(model=content_type)
        user_lst = []
        for item in queryset:
            notification, created = UserNotification.objects.get_or_create(
                user=item.support, content_type=content_type_obj
            )
            if created and not notification.is_active:
                notification.is_active = True
                notification.save()
            else:
                if notification.count <= 4 or not notification.is_active:
                    notification.count = 1
                    notification.is_active = True
                if not notification.is_active:
                    notification.is_active = True
                notification.save()
            user_lst.append(item.support.employee_id)
        return user_lst

    @staticmethod
    def get_project_update_pending():
        today = date.today()
        seven_days_ago = today - timedelta(days=7)
        one_day_ago = today - timedelta(days=1)

        active_projects = Q(~Q(project__updates__created__gte=seven_days_ago), start__lte=seven_days_ago,
                            statuses__created__lte=seven_days_ago,
                            statuses__frequency__in=['active', 'less_active'])

        training_projects = Q(~Q(project__updates__created__gte=one_day_ago),
                              project__start_date__gte=date.today())

        project_support_persons = ProjectSupport.objects.filter(
            Q(end__isnull=True, is_proxy_support=False, statuses__is_current=True,
              project__support_required=True) & (
                    active_projects | training_projects)).order_by('project__id').distinct('project__id')
        return project_support_persons

    @staticmethod
    def get_consultant_feedback_pending():
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        fourteen_days_ago = today - timedelta(days=14)

        # Query to fetch the project support instances
        active_projects = ~Q(project__feedbacks__created__gte=thirty_days_ago,
                             project__feedbacks__feedback_type__in=["independent", "2_week",
                                                                    "engineering_issue", "monthly"]) & Q(
            project__start_date__lte=thirty_days_ago
        )

        initial_projects = ~Q(project__feedbacks__created__gte=fourteen_days_ago,
                              project__feedbacks__feedback_type__in=['independent', '2_week',
                                                                     'engineering_issue', "monthly"]) & Q(
            project__start_date__gte=thirty_days_ago, project__start_date__lte=fourteen_days_ago)

        feedback_due_support_persons = ProjectSupport.objects.filter(
            Q(end__isnull=True, project__support_required=True, is_proxy_support=False,
              statuses__is_current=True, statuses__frequency__in=['active', 'less_active'], ) &
            (active_projects | initial_projects)).order_by('project__id').distinct('project__id')

        return feedback_due_support_persons

    @staticmethod
    def get_supervisor_feedback_pending():
        interviews = Interview.objects.filter(
            start_time__gte=datetime.strptime("2022-05-04", "%Y-%m-%d"),
            end_time__lte=datetime.now(timezone('US/Eastern')).replace(tzinfo=timezone('UTC')) - timedelta(
                hours=4)
        ).exclude(
            status__in=["cancelled", "next_round", "offer", "failed", "scheduled", "rescheduled"]
        ).exclude(
            supervisor_feedback__question__form_name='interview'
        ).order_by('id').distinct('id')

        supervisor_ids = interviews.values_list('supervisor', flat=True).distinct()
        supervisor_list = User.objects.filter(id__in=supervisor_ids)
        sup_counter = []
        for supervisor in supervisor_list:
            content_type = ContentType.objects.get(model='interview')
            notification, created = UserNotification.objects.get_or_create(user=supervisor, content_type=content_type)
            if created and not notification.is_active:
                notification.is_active = True
                notification.save()
            else:
                if notification.count <= 4 or not notification.is_active:
                    notification.count = 1
                    notification.is_active = True
                if not notification.is_active:
                    notification.is_active = True
                notification.save()
            sup_counter.append(supervisor.employee_id)
        return sup_counter

    def handle(self, *args, **options):
        try:
            support_persons_qs = self.get_project_update_pending()
            support_counter = self.update_notification(support_persons_qs, 'project')

            feedback_pending_qs = self.get_project_update_pending()
            feedback_counter = self.update_notification(feedback_pending_qs, 'consultant')

            sup_counter = self.get_supervisor_feedback_pending()

            un_es_id = UserNotification.objects.filter(user__role__name='engineer').values_list('user__employee_id',
                                                                                                flat=True)
            counter = set(support_counter).union(set(feedback_counter)).union(set(sup_counter))
            difference = set(un_es_id).difference(counter)
            delete_noti = UserNotification.objects.filter(user__employee_id__in=list(difference))
            delete_noti.delete()

        except Exception as error:
            create_cron_error("job", error)
