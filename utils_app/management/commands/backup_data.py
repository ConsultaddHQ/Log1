import os
import time
import boto3
from django.core.management import BaseCommand


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for Creating Database Backup and storing on S3 Bucket"

    # A command must define handle()
    def handle(self, *args, **options):
        current_time = time.strftime(r"%d-%m-%Y", time.localtime())
        cmd = f"sudo -u postgres pg_dump -Fc {os.getenv('DB_NAME')} > data-{current_time}.db"
        os.system(cmd)

        # Upload To S3
        s3 = boto3.resource('s3')
        s3.meta.client.upload_file(f'data-{current_time}.db', os.getenv('AWS_STORAGE_BACKUP_BUCKET_NAME'),
                                   f'data-{current_time}.db')
        os.remove(f"data-{current_time}.db")
