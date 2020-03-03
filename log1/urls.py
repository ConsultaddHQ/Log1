import os
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.documentation import include_docs_urls

from utils_app.views import CityViewSets

from report.views import ScrumMeetingReport

from ckiller.views import CkillerSubmissionViewSet

from attachment.views import AttachmentView, AttachmentGetView

from project.mobile_api import TimeSheetViewSets, PayrollScheduleViewSets

from notification.views import EmployeeNotificationViewSet, ConsultantNotificationViewSet

from project.views import ProjectViewSets, EngineeringProjectsViewSets, FinanceTimeSheetViewSets

from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSets

from consultant.mobile_api import ConsultantAuthViewSets, ConsultantAppViewSets, ConsultantResetPasswordViewSets

from marketing.views import VendorCompanyViewSets, VendorContactViewSets, LeadViewSets, SubmissionViewSets, \
    InterviewViewSets, VendorLayerViewSets

from consultant.views import ConsultantBenchViewSets, ConsultantViewSets, ConsultantMarketingViewSets, \
    ConsultantProfileViewSets, ConsultantPOCViewSets, WorkAuthViewSets


schema_view = get_swagger_view(title="New Log1 Documentation")

router = DefaultRouter()

router.register(r'asset', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'password', ResetPasswordViewSets)

router.register(r'attachment', AttachmentView)
router.register(r'get_attachment', AttachmentGetView)

router.register(r'consultant', ConsultantViewSets)
router.register(r'consultant_poc', ConsultantPOCViewSets)
router.register(r'consultant_work_auth', WorkAuthViewSets)
router.register(r'consultant_bench', ConsultantBenchViewSets)
router.register(r'consultant_profile', ConsultantProfileViewSets)
router.register(r'consultant_marketing', ConsultantMarketingViewSets)
router.register(r'consultant_password', ConsultantResetPasswordViewSets)

# Mobile Application routes
router.register(r'consultant_app', ConsultantAppViewSets)
router.register(r'consultant_auth', ConsultantAuthViewSets)

router.register(r'lead', LeadViewSets)
router.register(r'interview', InterviewViewSets)
router.register(r'submission', SubmissionViewSets)
router.register(r'vendor_layer', VendorLayerViewSets)
router.register(r'vendor_company', VendorCompanyViewSets)
router.register(r'vendor_contact', VendorContactViewSets)

router.register(r'project', ProjectViewSets)
router.register(r'timesheet', TimeSheetViewSets)
router.register(r'payroll', PayrollScheduleViewSets)
router.register(r'finance', FinanceTimeSheetViewSets)
router.register(r'eng_project', EngineeringProjectsViewSets)

router.register(r'city', CityViewSets)

router.register(r'report', ScrumMeetingReport)

router.register(r'ckiller_data', CkillerSubmissionViewSet)

router.register(r'emp_notify', ScrumMeetingReport)
router.register(r'con_notify', ScrumMeetingReport)


urlpatterns = [
    path('api/v2/', include(router.urls)),
    path('api/v2/admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.getenv('DEBUG', False):
    urlpatterns.append(path('api/v2/swagger/', schema_view))
    urlpatterns.append(path('api/v2/docs/', include_docs_urls(title='New Log1', public=True)))
