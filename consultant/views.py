import logging
from datetime import datetime, date
from django.db.models import Subquery, OuterRef, Q, F, Count
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView

from consultant.serializers import *

logger = logging.getLogger(__name__)


class ConsultantBenchViewSets(viewsets.ModelViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='map')
    def map(self, request):
        consultants = Consultant.objects.filter(status='in_marketing').values('current_city').annotate(
            total=Count('current_city')).order_by('current_city')
        return Response({"results": consultants}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        try:
            consultant_id = kwargs.get('pk')
            consultant = get_object_or_404(Consultant, id=consultant_id)
            serializer = self.serializer_class(consultant)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        team_name = request.query_params.get('team', None)
        con_status = request.query_params.get('status', 'in_marketing')
        query = request.query_params.get('query', None)
        location = request.query_params.get('location', None)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        if 'query' in request.query_params:
            if len(query.strip()) == 0:
                query = 'empty'
        try:
            consultants = Consultant.objects.filter(marketing__end=None).exclude(
                status__in=['new', 'archived', 'in_training', 'terminated'])
            # Team wise Filter
            if team_name:
                team = get_object_or_404(Team, name=team_name)
                consultants = consultants.filter(marketing__teams=team)

            # Location wise Filter
            if location:
                con_status = 'in_marketing'
                consultants = consultants.filter(current_city=location, status='in_marketing')

            # Consultants search based on name, email, recruiter and location
            elif query:
                consultants = consultants.objects.filter(
                    Q(name=query) |
                    Q(email=query) |
                    Q(skills=query) |
                    Q(current_city=query) |
                    Q(pocs__poc__employee_name__istartswith=query, pocs__end=None)
                )
                # Marketer's team Consultants
            else:
                consultants = Consultant.objects.filter(
                    Q(marketing__teams=request.user.team, marketing__in_pool=False) |
                    Q(marketing__marketer=request.user)
                )
            consultants = consultants.order_by('id').distinct('id')
            in_pool = consultants.filter(status='in_marketing', marketing__in_pool=True).count()
            in_marketing = consultants.filter(status='in_marketing', marketing__in_pool=False).count()

            count = {
                "total": in_pool + in_marketing,
                "in_pool": in_pool,
                "in_marketing": in_marketing
            }

            # Filter Consultant by status and In pool
            if con_status == 'in_pool':
                consultants = consultants.filter(status='in_marketing', marketing__in_pool=True)
            else:
                consultants = consultants.filter(status='in_marketing', marketing__in_pool=False)
            con_marketing = ConsultantPOC.objects.filter(
                consultant=OuterRef("pk"), end=None, poc_type='recruiter')
            data = consultants[first:last].annotate(
                preferred_location=F('marketing__preferred_location'),
                recruiter=Subquery(con_marketing.values('poc__employee_name')[:1])
            ).values('id', 'name', 'skills', 'preferred_location', 'recruiter')
            return Response({"results": data, "count": count}, status=status.HTTP_200_OK)

        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
