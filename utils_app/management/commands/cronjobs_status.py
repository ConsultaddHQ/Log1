from dateutil import tz
from django.core.management import BaseCommand

from constance import config
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        try:
            to_zone = tz.gettz('Asia/Kolkata')
            jobs = CronJob.objects.filter(enabled=True)
            text = """<tr>
                        <th style="padding:5px 8px 5px 8px;">Name</th>
                        <th style="padding:5px 8px 5px 8px;">Triggered At</th>
                    </tr>"""
            for job in jobs:
                text += f"""
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">{job.name}</td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;">
                                {job.modified.astimezone(to_zone).strftime('%l:%M %p %Z on %b %d, %Y')}</td>
                            </tr>
                        """
            data = {
                "title": "CronJob Status &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            post_msg_using_webhook(config.products_dev, data)
        except Exception as error:
            print(error)
