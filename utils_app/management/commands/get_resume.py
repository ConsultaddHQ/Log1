import os
import time

from django.conf import settings
from django.core.management import BaseCommand

from marketing.models import Submission
from attachment.models import Attachment
from utils_app.aws_utils import get_aws_connection


def get_file_name(obj):
    return os.path.split(obj.attachment_file.name)[1]


aws_key = f"https://s3.ap-south-1.amazonaws.com/log1-prod-media-v1.1/media/attachments/marketing_submission"

s3 = get_aws_connection()


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            titles = [
                    "Senior IT Architect", "Database Engineer", "Developer", "Senior Application Administrator",
                    "Senior Developer", "Information System Engineer", "Solutions Architect", "Java Developer"
                ]
            for title in titles:
                submissions = Submission.objects.filter(lead__job_title__icontains=title)
                if submissions:
                    print(submissions.first().lead.job_title)
                count = 0
                for sub in submissions:
                    if count >= 10:
                        break
                    count += 1
                    attachment = Attachment.objects.filter(
                        content_type__model='submission', object_id=sub.id, attachment_type='resume'
                    )
                    for obj in attachment:
                        key = obj.attachment_file.name
                        folder = f"{key.split('/')[1]}_"
                        ext = key.split('/')[3].split(".")[-1]
                        name = ".".join(key.split('/')[3].split(".")[:-1])
                        file_name = f"{folder}/{name}_{time.strftime('%Y%m%d-%H%M%S')}.{ext}"

                        if not os.path.exists(f"{settings.BASE_DIR}/media/{folder}"):
                            os.mkdir(f"{settings.BASE_DIR}/media/{folder}")
                        if not s3:
                            return "Unable to create Connection-download_s3_object", True

                        s3.download_file(os.getenv('AWS_STORAGE_BUCKET_NAME'), f'media/{key}', f'media/{file_name}')
        except Exception as error:
            print(error)
