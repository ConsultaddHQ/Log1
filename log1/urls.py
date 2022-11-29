import os
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.documentation import include_docs_urls

from activity.views import CommentViewSet
from impersonate.views import ImpersonateViewSets
from ckiller.views import CkillerSubmissionViewSet
from dashboard.views import MarketingDashboardViewSet
from messaging.views import SMSViewSet, ReceiveSMSViewSet
from legal.views import PetitionViewSets, PetitionDocsViewSets
from attachment.views import AttachmentView, AttachmentGetView
from utils_app.views import CityViewSet, ChoiceViewSet, TeamsTargetViewSet, UtilityViewSet
from project.mobile_api import PayrollScheduleViewSet, TimeSheetViewSet, TimeSheetV2ViewSet, ConsultantLeaveViewSet
from notification.views import EmployeeNotificationViewSet, ConsultantNotificationViewSet, FCMDeviceViewSet
from consultant.mobile_api import ConsultantAuthViewSet, ConsultantAppViewSet, ConsultantResetPasswordViewSet
from report.views import ScrumMeetingReport, SlashCommandViewSets, EngineeringReportViewSets, MarketingReportViewSets
from project.views import ProjectViewSets, EngineeringProjectsViewSets, FinanceTimeSheetViewSets, \
    ProjectOrderViewSet, ProjectSupportViewSet, LeaveManagementViewSets
from engineering.views import EngineeringViewSet, ProjectUpdateViewSet, ProjectSummaryViewSet, TrainingAgendaViewSet, \
    TrainingCheckListViewSet, EngineerReportViewSet, TeamStructureViewSet
from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSets, \
    AllUsersViewSet, HandoverViewSets, LoginViewSet, DefaultCalendarViewSets, CertificateViewSets
from marketing.views import VendorCompanyViewSets, VendorContactViewSets, LeadViewSets, SubmissionViewSets, \
    InterviewViewSets, VendorLayerViewSets, TestViewSets, SubmissionV2ViewSets, QuestionViewSets
from consultant.views import ConsultantBenchViewSets, ConsultantViewSets, ConsultantProfileViewSets, WorkAuthViewSets, \
    ConsultantPOCViewSets, ConsultantMarketingViewSets, ConsultantPetitionAuthViewSet, ConsultantExitViewSets,\
    ConsultantImportViewSet, ConsultantV2ViewSets, ConsultantFeedbackViewSet
from dynamic_report.views import ReportsViewSets



router = DefaultRouter()
schema_view = get_swagger_view(title='Log1')

router.register(r'login', LoginViewSet)
router.register(r'users', AllUsersViewSet)
router.register(r'assets', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'handover', HandoverViewSets)
router.register(r'password', ResetPasswordViewSets)
router.register(r'calendar_info', DefaultCalendarViewSets)
router.register(r'employee_certificate', CertificateViewSets)


router.register(r'attachment', AttachmentView)
router.register(r'get_attachment', AttachmentGetView)

router.register(r'consultant', ConsultantViewSets)
router.register(r'consultant_poc', ConsultantPOCViewSets)
router.register(r'consultant_work_auth', WorkAuthViewSets)
router.register(r'consultant_exit', ConsultantExitViewSets)
router.register(r'beats_consultant', ConsultantImportViewSet)
router.register(r'consultant_bench', ConsultantBenchViewSets)
router.register(r'consultant_profile', ConsultantProfileViewSets)
router.register(r'consultant_marketing', ConsultantMarketingViewSets)
router.register(r'consultant/(?P<consultant_id>[0-9]+)/feedback', ConsultantFeedbackViewSet)

router.register(r'test', TestViewSets)
router.register(r'lead', LeadViewSets)
router.register(r'question', QuestionViewSets)
router.register(r'interview', InterviewViewSets)
router.register(r'submission', SubmissionViewSets)
router.register(r'vendor_layer', VendorLayerViewSets)
router.register(r'dashboard', MarketingDashboardViewSet)
router.register(r'vendor_company', VendorCompanyViewSets)
router.register(r'vendor_contact', VendorContactViewSets)

router.register(r'project', ProjectViewSets)
router.register(r'dynamic_reports', ReportsViewSets)
router.register(r'finance', FinanceTimeSheetViewSets)
router.register(r'project_order', ProjectOrderViewSet)
router.register(r'team_structure', TeamStructureViewSet)
router.register(r'engineer_report', EngineerReportViewSet)
router.register(r'eng_project', EngineeringProjectsViewSets)
router.register(r'project/(?P<project_id>[0-9]+)/updates', ProjectUpdateViewSet)
router.register(r'project/(?P<project_id>[0-9]+)/support', ProjectSupportViewSet)
router.register(r'project/(?P<project_id>[0-9]+)/summary', ProjectSummaryViewSet)
router.register(r'project/(?P<project_id>[0-9]+)/training', TrainingAgendaViewSet)
router.register(r'project/(?P<project_id>[0-9]+)/checklist', TrainingCheckListViewSet)
router.register(r'finance/(?P<consultant_id>[0-9]+)/leave', LeaveManagementViewSets)

router.register(r'city', CityViewSet)
router.register(r'choice', ChoiceViewSet)

router.register(r'cmd', SlashCommandViewSets)

router.register(r'report', ScrumMeetingReport)
router.register(r'support_report', EngineeringReportViewSets)
router.register(r'marketing_report', MarketingReportViewSets)

router.register(r'comment', CommentViewSet)

router.register(r'impersonate', ImpersonateViewSets)

router.register(r'ckiller_data', CkillerSubmissionViewSet)

router.register(r'fcm', FCMDeviceViewSet)
router.register(r'emp_notify', EmployeeNotificationViewSet)
router.register(r'con_notify', ConsultantNotificationViewSet)

router.register(r'engineering', EngineeringViewSet)

# Mobile App routes
router.register(r'consultant_app', ConsultantAppViewSet)
router.register(r'consultant_auth', ConsultantAuthViewSet)
router.register(r'consultant_password', ConsultantResetPasswordViewSet)

router.register(r'timesheet', TimeSheetViewSet)
router.register(r'payroll', PayrollScheduleViewSet)
router.register(r'timesheet_v2', TimeSheetV2ViewSet)
router.register(r'consultant_leave', ConsultantLeaveViewSet)

router.register(r'utility', UtilityViewSet)
router.register(r'util', TeamsTargetViewSet)

# Legal App routes
router.register(r'petition', PetitionViewSets)
router.register(r'petition_docs', PetitionDocsViewSets)
router.register(r'consultant_petition', ConsultantPetitionAuthViewSet)

# Twilio messaging app routes
router.register(r'twilio', SMSViewSet)
router.register(r'twilio_receive', ReceiveSMSViewSet)

router_v2 = DefaultRouter()

router_v2.register(r'submission', SubmissionV2ViewSets)
router_v2.register(r'consultant', ConsultantV2ViewSets)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/admin/', admin.site.urls),
    path('api/v2/', include(router_v2.urls)),
    path('api/explorer/', include('explorer.urls')),
    path('api/swagger/', schema_view),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.getenv('DEBUG', 'False') == 'True':
    urlpatterns.append(path('api/docs/', include_docs_urls(title='Log1', public=True)))
