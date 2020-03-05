from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        queryset = Consultant.objects.filter(marketing__status='open')
        on_project_con = queryset.filter(status='on_project').count()
        in_pool_con = queryset.filter(status='on_bench', marketing__in_pool=True).count()
        on_bench_con = queryset.filter(status='on_bench', marketing__in_pool=False).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Bench Status :memo: \n
| Consultant Status | Count            |
|:------------------|:-----------------|
| In Marketing      | {on_bench_con}   |
| In Pool           | {in_pool_con}    | 
| On Project        | {on_project_con} | 
"""
        }

        post_msg_using_webhook(config.recruitment_url, data)
