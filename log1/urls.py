import os
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.documentation import include_docs_urls

from utils_app.views import CityViewSets, WebHookViewSet

from ckiller.views import CkillerSubmissionView

from impersonate.views import ImpersonateViewSets

from messaging.views import SMSViewSet, ReceiveSMSViewSet

from ckiller.views import CkillerSubmissionViewSet

from attachment.views import AttachmentView, AttachmentGetView

from report.views import ScrumMeetingReport, SlashCommandViewSets

from legal.views import PetitionViewSets, PetitionDocsViewSets

from notification.views import EmployeeNotificationViewSet, ConsultantNotificationViewSet

from project.views import ProjectViewSets, EngineeringProjectsViewSets, FinanceTimeSheetViewSets

from project.mobile_api import TimeSheetViewSets, PayrollScheduleViewSets, TimeSheetV2ViewSets, Test

from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSets, \
    AllUsersViewSet

from consultant.mobile_api import ConsultantAuthViewSet, ConsultantAppViewSet, ConsultantResetPasswordViewSet

from marketing.views import VendorCompanyViewSets, VendorContactViewSets, LeadViewSets, SubmissionViewSets, \
    InterviewViewSets, VendorLayerViewSets

from consultant.views import ConsultantBenchViewSets, ConsultantViewSets, ConsultantProfileViewSets, WorkAuthViewSets, \
    ConsultantPOCViewSets, ConsultantMarketingViewSets, ConsultantPetitionAuthViewSet, ConsultantExitViewSets,\
    FeedbackViewSet

from activity.views import CommentViewSet

SCHEMA_VIEW = get_swagger_view(title="New Log1 Documentation")

router = DefaultRouter()

router.register(r'users', AllUsersViewSet)
router.register(r'assets', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'password', ResetPasswordViewSets)

router.register(r'attachment', AttachmentView)
router.register(r'get_attachment', AttachmentGetView)

router.register(r'feedback', FeedbackViewSet)
router.register(r'consultant', ConsultantViewSets)
router.register(r'consultant_poc', ConsultantPOCViewSets)
router.register(r'consultant_work_auth', WorkAuthViewSets)
router.register(r'consultant_exit', ConsultantExitViewSets)
router.register(r'consultant_bench', ConsultantBenchViewSets)
router.register(r'consultant_profile', ConsultantProfileViewSets)
router.register(r'consultant_marketing', ConsultantMarketingViewSets)

router.register(r'lead', LeadViewSets)
router.register(r'interview', InterviewViewSets)
router.register(r'submission', SubmissionViewSets)
router.register(r'vendor_layer', VendorLayerViewSets)
router.register(r'vendor_company', VendorCompanyViewSets)
router.register(r'vendor_contact', VendorContactViewSets)

router.register(r'project', ProjectViewSets)
router.register(r'finance', FinanceTimeSheetViewSets)
router.register(r'eng_project', EngineeringProjectsViewSets)

router.register(r'city', CityViewSets)
router.register(r'hook', WebHookViewSet)

router.register(r'cmd', SlashCommandViewSets)

router.register(r'report', ScrumMeetingReport)

router.register(r'comment', CommentViewSet)

router.register(r'impersonate', ImpersonateViewSets)

router.register(r'ckiller_data', CkillerSubmissionView)

router.register(r'emp_notify', EmployeeNotificationViewSet)
router.register(r'con_notify', ConsultantNotificationViewSet)


# Mobile Application routes
router.register(r'consultant_app', ConsultantAppViewSet)
router.register(r'consultant_auth', ConsultantAuthViewSet)
router.register(r'consultant_password', ConsultantResetPasswordViewSet)

router.register(r'timesheet', TimeSheetViewSets)
router.register(r'payroll', PayrollScheduleViewSets)
router.register(r'timesheet_v2', TimeSheetV2ViewSets)

router.register(r'test', Test)

# Legal App APIs
router.register(r'petition', PetitionViewSets)
router.register(r'petition_docs', PetitionDocsViewSets)
router.register(r'consultant_petition', ConsultantPetitionAuthViewSet)

router.register(r'twilio', SMSViewSet)
router.register(r'twilio_receive', ReceiveSMSViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/admin/', admin.site.urls),
    path('api/explorer/', include('explorer.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.getenv('DEBUG', 'False') == 'True':
    urlpatterns.append(path('api/swagger/', SCHEMA_VIEW))
    urlpatterns.append(path('api/docs/', include_docs_urls(title='New Log1', public=True)))
