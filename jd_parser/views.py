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

    def retrieve(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(MMailScrap, id=kwargs.get("pk"))
            serializer = MarketingMailSerializer(update)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            # write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
