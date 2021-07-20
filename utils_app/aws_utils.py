import os
import time
import boto3
from django.conf import settings
from log1.utils import write_exception
from botocore.exceptions import ClientError


def get_aws_connection():
    try:
        s3 = boto3.client(
            's3', region_name=os.getenv('AWS_REGION_NAME'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        return s3
    except ClientError as error:
        write_exception(message=error)
        return None


def get_s3_object(key):
    try:
        s3 = get_aws_connection()
        if not s3:
            return "Unable to create Connection", True

        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': os.getenv('AWS_STORAGE_BUCKET_NAME'),
                'Key': f'media/{key}'
            },
            ExpiresIn=3600
        )
        return url, False
    except Exception as error:
        write_exception(message=error)
        return str(error), True


def download_s3_object(key):
    try:
        folder = key.split('/')[1]
        ext = key.split('/')[3].split(".")[-1]
        name = ".".join(key.split('/')[3].split(".")[:-1])
        file_name = f"{folder}/{name}_{time.strftime('%Y%m%d-%H%M%S')}.{ext}"

        if not os.path.exists(f"{settings.BASE_DIR}/media/{folder}"):
            os.mkdir(f"{settings.BASE_DIR}/media/{folder}")

        s3 = get_aws_connection()
        if not s3:
            return "Unable to create Connection", True

        s3.download_file(os.getenv('AWS_STORAGE_BUCKET_NAME'), f'media/{key}', f'media/{file_name}')
        return f'media/{file_name}', False
    except Exception as error:
        write_exception(message=error)
        return str(error), True


def download_s3_object_beats(key, name):
    try:
        local_path = f'media/beats/{name}'
        s3 = get_aws_connection()
        if s3:
            return "Unable to create Connection", True
        s3.download_file(os.getenv('AWS_BEATS_BUCKET'), key, local_path)
        return local_path, False
    except Exception as error:
        write_exception(message=error)
        return str(error), True


def presigned_post_url(object_name, fields=None, conditions=None, expiration=3600):
    try:
        s3 = get_aws_connection()
        if not s3:
            return "Unable to create Connection", True

        bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
        response = s3.generate_presigned_post(
            bucket_name, object_name, Fields=fields, Conditions=conditions, ExpiresIn=expiration
        )
        return response, False
    except Exception as error:
        write_exception(message=error)
        return str(error), True
