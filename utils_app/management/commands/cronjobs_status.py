from dateutil import tz
from datetime import date
from django.core.management import BaseCommand

from constance import config
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook


class Command(BaseCommand):
    help = "This command is for posting CronJobs status"

    def handle(self, *args, **options):
        try:
            to_zone = tz.gettz('Asia/Kolkata')
            jobs = CronJob.objects.filter(enabled=True)
            text = """<tr>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Name</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Triggered At</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Error</th>
                    </tr>"""
            for job in jobs:
                errors = " :: ".join(job.errors.filter(created__date=date.today()).values('description'))
                text += f"""
                            <tr>
                                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{" ".join(job.name.split("_")).title()}</td>
                                <td style="padding:5px 8px 5px 8px;font-size: 2.5em; text-align: center;">
                                {job.modified.astimezone(to_zone).strftime('%l:%M %p %Z on %b %d, %Y')}</td>
                                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{errors}</td>
                            </tr>
                        """
            data = {
                "title": "CronJob Status &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
            }

            # post_msg_using_webhook(config.products_dev, data)
        except Exception as error:
            print(error)
