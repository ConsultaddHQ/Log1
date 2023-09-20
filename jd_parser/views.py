from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from jd_parser.models import MarketingMail, MMailScrap
from jd_parser.serializers import MarketingMailListSerializer, MarketingMailSerializer
from log1.utils import ERROR_MSG


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 10000


class MarketingMailListViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = MMailScrap.objects.all().order_by("-date")
    permission_classes = (IsAuthenticated,)
    serializer_class = MarketingMailListSerializer
    pagination_class = LargeResultsSetPagination
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        roleTechStack = {
            "frontend": [
                "javascript",
                "react",
                "angular",
                "vue",
                "next",
                "jquery",
                "php",
                "perl",
                "ruby",
                "asp.net",
                "frontend",
                "front end",
                "frontend developer",
            ],
            "backend": [
                "python",
                "java",
                "c#",
                ".net",
                "nodejs",
                "django",
                "flask",
                "fastapi",
                "spring boot",
                "backend",
                "back end",
                "backend developer",
            ],
            "database": [
                "sql",
                "mysql",
                "postgres",
                "postgresql",
                "oracle",
                "oracle sql",
                "mongodb",
                "dbsqilte3",
                "dbsqilte",
                "dynamodb",
                "database",
                "database developer",
            ],
            "devops": [
                "aws",
                "aws cli",
                "azure",
                "jenkins",
                "ci/cd",
                "pipeline",
                "docker",
                "kubernetes",
                "ansible",
                "terraform",
                "devops",
                "devops developer",
            ],
        }
        role = request.GET.get("role", None)
        requirmentMail = request.GET.get("requirmentMail", None)
        try:
            queryset = self.filter_queryset(self.get_queryset())
            queryset = (
                queryset.exclude(body_text__isnull=True)
                .exclude(body_text__exact="")
                .exclude(requirmentMail=requirmentMail)
            )
            if role:
                filters = Q()
                if role.lower() != "fullstack":
                    techs = roleTechStack[role.lower()]
                    for tech in techs:
                        filters |= Q(keywords__contains=tech + ";")
                else:
                    backendTechs = roleTechStack["backend"]
                    frontendTechs = roleTechStack["frontend"]

                    backendFilter = Q()
                    frontendFilter = Q()
                    for tech in backendTechs:
                        backendFilter |= Q(keywords__contains=tech + ";")
                    for tech in frontendTechs:
                        frontendFilter |= Q(keywords__contains=tech + ";")
                    filters = backendFilter & frontendFilter

                queryset = queryset.filter(filters)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)

            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(MMailScrap, id=kwargs.get("pk"))
            serializer = MarketingMailSerializer(update)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            # write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
