from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from api_key.permissions import HasReadOnlyAPIKey
from consultant.models import ConsultantMarketing


class BenchConsultantSnapshotView(APIView):
    """Read-only, deliberately narrow data feed for the NightShift adapter."""

    authentication_classes = ()
    permission_classes = (HasReadOnlyAPIKey,)

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        next_week_start = week_start + timedelta(days=7)

        completed_this_week = Q(
            submissions__is_complete=True,
            submissions__created__gte=week_start,
            submissions__created__lt=next_week_start,
        )
        records = (
            ConsultantMarketing.objects
            .filter(consultant__status="on_bench", status="open", marketer__isnull=False)
            .annotate(
                weekly_completed_submission_count=Count(
                    "submissions__id",
                    filter=completed_this_week,
                    distinct=True,
                )
            )
            .values(
                "consultant_id",
                "consultant__name",
                "consultant__status",
                "marketer__id",
                "marketer__employee_name",
                "weekly_completed_submission_count",
            )
            .order_by("consultant_id", "marketer__id")
        )

        data = [
            {
                "consultant_id": record["consultant_id"],
                "consultant_name": record["consultant__name"],
                "marketer_id": record["marketer__id"],
                "marketer_name": record["marketer__employee_name"],
                "bench_status": record["consultant__status"],
                "weekly_completed_submission_count": record["weekly_completed_submission_count"],
            }
            for record in records
        ]
        return Response({"data": data})
