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
    ConsultantProfileViewSets
from marketing.views import VendorCompanyViewSets

schema_view = get_swagger_view(title='New Log1 Documentation')

router = DefaultRouter()

router.register(r'asset', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'password', ResetPasswordViewSets)

router.register(r'consultant', ConsultantViewSets)
router.register(r'consultant_bench', ConsultantBenchViewSets)
router.register(r'consultant_profile', ConsultantProfileViewSets)
router.register(r'consultant_marketing', ConsultantMarketingViewSets)

router.register(r'vendor_company', VendorCompanyViewSets)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/swagger/', schema_view),
    path('api/admin/', admin.site.urls),
    path('api/docs/', include_docs_urls(title='New Log1', public=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
