from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.documentation import include_docs_urls

from employee.views import EmployeeAuthViewSets, EmployeeViewSets, AssetsViewSets, ResetPasswordViewSet
from consultant.views import ConsultantBenchViewSets

schema_view = get_swagger_view(title='New Log1 Documentation')

router = DefaultRouter()

router.register(r'asset', AssetsViewSets)
router.register(r'auth', EmployeeAuthViewSets)
router.register(r'employee', EmployeeViewSets)
router.register(r'password', ResetPasswordViewSet)

router.register(r'consultant', ConsultantBenchViewSets)


urlpatterns = [
    path('api/', include(router.urls)),
    path(r'api/swagger/', schema_view),
    path('api/admin/', admin.site.urls),
    path('api/docs/', include_docs_urls(title='New Log1', public=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
