from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.urls import path

schema_view = get_schema_view(
    openapi.Info(
        title="LOG1 API Documentation",
        default_version='v1',
        description="API documentation for LOG1",
        # terms_of_service="https://www.example.com/policies/terms/",
        contact=openapi.Contact(email="vishesh.s@consultadd.com"),
    ),
    public=True,
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
