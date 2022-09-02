from django.contrib.auth.models import ContentType
from django.core.management import BaseCommand

from attachment.models import Attachment
from utils_app.aws_utils import *
from utils_app.utils import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='dump s3')
        try:
            fail, done = 0, 0
            content_type = ContentType.objects.get(model='timesheet')
            att = Attachment.objects.filter(created__gt='2022-06-01').exclude(content_type=content_type)
            # s3_prod = boto3.client(
            #     's3', region_name=os.getenv('AWS_REGION_NAME'),
            #     aws_access_key_id='AKIAUST3UQC6JLPRTYXD',
            #     aws_secret_access_key='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'
            # )
            s3_prod = get_aws_connection()
            s3_local = get_aws_connection()
            print("Dumping Started")
            for a in att:
                key = a.attachment_file.name
                response, error = get_s3_object(key)
                if error:
                    fail += 1
                    print(error)
                    continue
                try:
                    # obj = s3_prod.get_object(Bucket='log1-prod-media', Key=f'media/{key}')
                    obj = s3_prod.get_object(Bucket='log1dev', Key=f'media/{key}')
                except Exception as e:
                    print(error)
                    fail += 1
                    continue
                file = obj['Body'].read()
                # s3_local.put_object(Body=file, Key=f'media/{a.attachment_file.name}',
                #               ContentType=obj['ResponseMetadata']['HTTPHeaders']['content-type'],
                #               Bucket=f'{os.getenv("AWS_STORAGE_BUCKET_NAME")}')
                s3_local.put_object(Body=file, Key=f'media/{a.attachment_file.name}',
                              ContentType=obj['ResponseMetadata']['HTTPHeaders']['content-type'],
                              Bucket=f'bugtracking')
                done += 1
                print(f"{a.attachment_file.name} dumped successfully")
            print(f"Passed:--{done}")
            print(f"Failed:--{fail}")
        except Exception as error:
            print(error)
