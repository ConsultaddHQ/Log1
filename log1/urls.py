import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.documentation import include_docs_urls
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from activity.views import CommentViewSet
from attachment.views import AttachmentGetView, AttachmentView
from ckiller.views import CkillerSubmissionViewSet
from dashboard.views import MarketingDashboardViewSet, QuickActionsViewSets
from impersonate.views import ImpersonateViewSets
from jd_parser.views import MarketingMailListViewSet
from legal.views import PetitionViewSets, PetitionDocsViewSets
from messaging.views import SMSViewSet, ReceiveSMSViewSet
from utils_app.views import CityViewSet, ChoiceViewSet, TeamsTargetViewSet, UtilityViewSet
from finance.views import FinanceLeaveViewSets, FinancePayStubsViewSets, FinanceTimeSheetViewSet,\
    LeaveBalanceViewSets
from project.mobile_api import PayrollScheduleViewSet, TimeSheetViewSet, ConsultantLeaveViewSet, \
    TimetrackEventMobileViewSet
from notification.views import EmployeeNotificationViewSet, ConsultantNotificationViewSet, FCMDeviceViewSet
from consultant.mobile_api import ConsultantAuthViewSet, ConsultantAppViewSet, ConsultantResetPasswordViewSet
from report.views import ScrumMeetingReport, SlashCommandViewSets, EngineeringReportViewSets, MarketingReportViewSets, \
    EngineerReportXposedViewSets, DetailedReportViewSets, ConsultantDetailReportViewSets
from engineering.views import EngineeringViewSet, ProjectUpdateViewSet, ProjectSummaryViewSet, TrainingAgendaViewSet, \
    TrainingCheckListViewSet, EngineerReportViewSet, EngineeringTeamViewSet
from project.views import ProjectViewSets, EngineeringProjectsViewSets, FinanceTimeSheetViewSets, \
    ProjectOrderViewSet, ProjectSupportViewSet, LeaveManagementViewSets, TimetrackEventViewSet, \
    ConsultantRevisionViewSet, ProjectPaymentTermViewSet, ProjectAssociatesViewSet
from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSets, \
    AllUsersViewSet, HandoverViewSets, LoginViewSet, DefaultCalendarViewSets, CertificateViewSets
from marketing.views import VendorCompanyViewSets, VendorContactViewSets, LeadViewSets, SubmissionViewSets, \
    InterviewViewSets, VendorLayerViewSets, TestViewSets, SubmissionV2ViewSets, QuestionViewSets, MarketingTeamViewSet, \
    MarketingAPIViewSet
from consultant.views import ConsultantBenchViewSets, ConsultantViewSets, ConsultantProfileViewSets, WorkAuthViewSets, \
    ConsultantPOCViewSets, ConsultantMarketingViewSets, ConsultantPetitionAuthViewSet, ConsultantExitViewSets, \
    ConsultantImportViewSet, ConsultantV2ViewSets, ConsultantFeedbackViewSet, ConsultantPerformanceViewSet
from user_api.views import UserApiKeyViewSet, MarketingPublicApiViewSet

router = DefaultRouter()
schema_view = get_schema_view(
    openapi.Info(
        title="Log1",
        default_version="v1",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router.register(r"login", LoginViewSet, basename="login")
router.register(r"users", AllUsersViewSet, basename="users")
router.register(r"assets", AssetsViewSets)
router.register(r"auth", EmployeeAuthViewSets, basename="auth")
router.register(r"employee", EmployeeViewSets, basename="employee")
router.register(r"handover", HandoverViewSets)
router.register(r"password", ResetPasswordViewSets, basename="password")
router.register(r"calendar_info", DefaultCalendarViewSets, basename="calendar_info")
router.register(r"employee_certificate", CertificateViewSets, basename="employee_certificate")


router.register(r"attachment", AttachmentView)
router.register(r"get_attachment", AttachmentGetView, basename="get_attachment")

router.register(r"consultant", ConsultantViewSets, basename="consultant")
router.register(r"consultant_poc", ConsultantPOCViewSets, basename="consultant_poc")
router.register(r"consultant_work_auth", WorkAuthViewSets, basename="consultant_work_auth")
router.register(r"consultant_exit", ConsultantExitViewSets, basename="consultant_exit")
router.register(r"beats_consultant", ConsultantImportViewSet, basename="beats_consultant")
router.register(r"consultant_bench", ConsultantBenchViewSets, basename="consultant_bench")
router.register(r"log1_consultant", ConsultantPerformanceViewSet, basename="log1_consultant")
router.register(r"consultant_profile", ConsultantProfileViewSets, basename="consultant_profile")
router.register(r"consultant_marketing", ConsultantMarketingViewSets, basename="consultant_marketing")
router.register(
    r"consultant/(?P<consultant_id>[0-9]+)/feedback", ConsultantFeedbackViewSet, basename="consultant_feedback"
)

router.register(r"test", TestViewSets, basename="test")
router.register(r"lead", LeadViewSets, basename="lead")
router.register(r"question", QuestionViewSets, basename="question")
router.register(r"interview", InterviewViewSets, basename="interview")
router.register(r"submission", SubmissionViewSets, basename="submission")
router.register(r"vendor_layer", VendorLayerViewSets, basename="vendor_layer")
router.register(r"dashboard", MarketingDashboardViewSet, basename="dashboard")
router.register(r"vendor_company", VendorCompanyViewSets, basename="vendor_company")
router.register(r"vendor_contact", VendorContactViewSets, basename="vendor_contact")
router.register(r"marketing_team", MarketingTeamViewSet, basename="marketing_team")

router.register(r"m_mail", MarketingMailListViewSet, basename="m_mail")
router.register(r"project", ProjectViewSets, basename="project")
router.register(r"finance", FinanceTimeSheetViewSets, basename="finance")
router.register(r"project_order", ProjectOrderViewSet, basename="project_order")
router.register(r"eng_team", EngineeringTeamViewSet, basename="eng_team")
router.register(r"engineer_report", EngineerReportViewSet, basename="engineer_report")
router.register(r"timesheet_event", TimetrackEventViewSet, basename="timesheet_event")
router.register(r"eng_project", EngineeringProjectsViewSets, basename="eng_project")
router.register(r"rate_revision", ConsultantRevisionViewSet, basename="rate_revision")
router.register(r"project_associates", ProjectAssociatesViewSet, basename="project_associates")
router.register(r'project_payment_term', ProjectPaymentTermViewSet, basename="project_payment_term")
router.register(r"project/(?P<project_id>[0-9]+)/updates", ProjectUpdateViewSet, basename="project_updates")
router.register(r"project/(?P<project_id>[0-9]+)/support", ProjectSupportViewSet, basename="project_support")
router.register(r"project/(?P<project_id>[0-9]+)/summary", ProjectSummaryViewSet, basename="project_summary")
router.register(r"project/(?P<project_id>[0-9]+)/training", TrainingAgendaViewSet, basename="project_training")
router.register(r"project/(?P<project_id>[0-9]+)/checklist", TrainingCheckListViewSet, basename="project_checklist")
router.register(r"finance/(?P<consultant_id>[0-9]+)/leave", LeaveManagementViewSets, basename="consultant_leave_management")
router.register(r"engineer_detail", MarketingAPIViewSet, basename="engineer_detail")

router.register(r"city", CityViewSet, basename="city")
router.register(r"choice", ChoiceViewSet, basename="choice")

router.register(r"cmd", SlashCommandViewSets, basename="cmd")

router.register(r"report", ScrumMeetingReport, basename="report")
router.register(r"report_detail", DetailedReportViewSets, basename="report_detail")
router.register(r"consultant_detail_report", ConsultantDetailReportViewSets, basename="consultant_detail_report")
router.register(r"engineers", EngineerReportXposedViewSets, basename="engineers")
router.register(r"support_report", EngineeringReportViewSets, basename="support_report")
router.register(r"marketing_report", MarketingReportViewSets, basename="marketing_report")

router.register(r"comment", CommentViewSet, basename="comment")

router.register(r"impersonate", ImpersonateViewSets, basename="impersonate")

router.register(r"quick_actions", QuickActionsViewSets, basename="quick_actions")

router.register(r"ckiller_data", CkillerSubmissionViewSet, basename="ckiller_data")

router.register(r"fcm", FCMDeviceViewSet, basename="fcm")
router.register(r"emp_notify", EmployeeNotificationViewSet, basename="emp_notify")
router.register(r"con_notify", ConsultantNotificationViewSet, basename="con_notify")

router.register(r"engineering", EngineeringViewSet, basename="engineering")

# Mobile App routes
router.register(r"consultant_app", ConsultantAppViewSet, basename="consultant_app")
router.register(r"consultant_auth", ConsultantAuthViewSet, basename="consultant_auth")
router.register(r"consultant_password", ConsultantResetPasswordViewSet, basename="consultant_password")

router.register(r"timesheet", TimeSheetViewSet, basename="timesheet")
router.register(r"payroll", PayrollScheduleViewSet, basename="payroll")
router.register(r"event", TimetrackEventMobileViewSet, basename="event")
router.register(r"consultant_leave", ConsultantLeaveViewSet, basename="consultant_leave")

router.register(r"utility", UtilityViewSet, basename="utility")
router.register(r"util", TeamsTargetViewSet, basename="util")

# Legal App routes
router.register(r"petition", PetitionViewSets, basename="petition")
router.register(r"petition_docs", PetitionDocsViewSets, basename="petition_docs")
router.register(r"consultant_petition", ConsultantPetitionAuthViewSet, basename="consultant_petition")

# finance App routes
router.register(r'leave_balance', LeaveBalanceViewSets, basename="leave_balance")
router.register(r'finance_leave', FinanceLeaveViewSets, basename="finance_leave")    #FinLeaveViewSets
router.register(r'finance_payStubs', FinancePayStubsViewSets, basename="finance_payStubs")    #FinStubsViewSets
router.register(r'finance_timesheet', FinanceTimeSheetViewSet, basename="finance_timesheet")  #FintimeViewSet

# Twilio messaging app routes
router.register(r"twilio", SMSViewSet, basename="twilio")
router.register(r"twilio_receive", ReceiveSMSViewSet, basename="twilio_receive")

#User api app routes
router.register(r"user_api", UserApiKeyViewSet, basename="user_api")
router.register(r"public_api", MarketingPublicApiViewSet, basename="public_api")

router_v2 = DefaultRouter()

router_v2.register(r"submission", SubmissionV2ViewSets, basename="submission_v2")
router_v2.register(r"consultant", ConsultantV2ViewSets, basename="consultant_v2")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/admin/", admin.site.urls),
    path("api/v2/", include(router_v2.urls)),
    path("api/explorer/", include("explorer.urls")),
    path("api/swagger/", schema_view.with_ui("swagger", cache_timeout=0)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.getenv("DEBUG", "False") == "True":
    urlpatterns.append(path("api/docs/", include_docs_urls(title="Log1", public=True)))
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
