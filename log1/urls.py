import os
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.documentation import include_docs_urls

from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSets
from consultant.views import ConsultantBenchViewSets, ConsultantViewSets, ConsultantMarketingViewSets, \
    ConsultantProfileViewSets, ConsultantAuthViewSets, ConsultantAppViewSets
from marketing.views import VendorCompanyViewSets, VendorContactViewSets, LeadViewSets, SubmissionViewSets, \
    InterviewViewSets
from utils_app.views import CityViewSets
from attachment.views import AttachmentView
from project.views import ProjectViewSets, EngineeringProjectsViewSets

schema_view = get_swagger_view(title='New Log1 Documentation')

router = DefaultRouter()

router.register(r'asset', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'password', ResetPasswordViewSets)

router.register(r'attachment', AttachmentView)

router.register(r'consultant', ConsultantViewSets)
router.register(r'consultant_bench', ConsultantBenchViewSets)
router.register(r'consultant_profile', ConsultantProfileViewSets)
router.register(r'consultant_marketing', ConsultantMarketingViewSets)

# Mobile Application routes
router.register(r'consultant_app', ConsultantAppViewSets)
router.register(r'consultant_auth', ConsultantAuthViewSets)

router.register(r'lead', LeadViewSets)
router.register(r'screening', InterviewViewSets)
router.register(r'submission', SubmissionViewSets)
router.register(r'vendor_company', VendorCompanyViewSets)
router.register(r'vendor_contact', VendorContactViewSets)

router.register(r'project', ProjectViewSets)
router.register(r'eng_project', EngineeringProjectsViewSets)

router.register(r'city', CityViewSets)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.getenv('DEBUG', False):
    urlpatterns.append(path('api/swagger/', schema_view))
    urlpatterns.append(path('api/docs/', include_docs_urls(title='New Log1', public=True)))
