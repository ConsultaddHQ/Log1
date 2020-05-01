from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        queryset = Consultant.objects.filter(marketing__status='open').exclude(status='archived').distinct()
        on_bench_con = queryset.count()
        in_pool_con = queryset.filter(marketing__in_pool=True).count()
        on_boarded = Consultant.objects.filter(
            projects__statuses__status='on_boarded',
            projects__statuses__is_current=True
        ).exclude(status='archived').distinct().count()
        joined = Consultant.objects.filter(
            projects__statuses__status='on_boarded',
            projects__statuses__is_current=True
        ).exclude(status='archived').distinct().count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Consultant Bench Status :memo: \n
| Status     | Count          |
|:-----------|:---------------|
| Bench      | {on_bench_con} |
| In Pool    | {in_pool_con}  | 
| On boarded | {on_boarded}   |
| Joined     | {joined}       |
"""
        }

        post_msg_using_webhook(config.recruitment_url, data)
