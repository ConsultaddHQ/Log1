import os
import csv
import boto3
from pytz import timezone
from datetime import datetime
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from utils_app.models import CronJob, CronError
from log1.utils import write_exception, write_info
from utils_app.mailing import send_email_without_template
from html2image import Html2Image


def create_table_image(data, filename=None):
    try:
        hti = Html2Image()
        filename = f"{filename}_{datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}"
        hti.screenshot(html_str=data, save_as=f'{filename}.png')
        return f'{filename}.png'
    except Exception as error:
        write_exception(message=error)


def upload_csv_file_s3(filename):
    try:
        file = open(f'{filename}', 'rb')
        session = boto3.Session()
        s3 = session.client(
            "s3", aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        file.seek(0)
        s3.put_object(Body=file, Key=f'{file.name}', ContentType='application/csv',
                      Bucket=f'{os.getenv("AWS_REPORT_STORAGE_BUCKET_NAME")}')
        file_url = f"https://{os.getenv('AWS_REPORT_STORAGE_BUCKET_NAME')}.s3.ap-south-1.amazonaws.com/{file.name}"
        delete_temp_file([file.name])
        return file_url
    except Exception as error:
        write_info(message=f"{error}", function='create_csv_file')


def create_csv_file(payload):
    try:
        filename = f"{payload.get('report_name')}_{datetime.now().strftime('%d-%B-%Y')}"
        file = open(f'{filename}.csv', 'w')
        writer = csv.writer(file)
        row_data = payload['data']
        writer.writerow(['CTB', 'Round', 'Type', 'Start Time', 'Consultant', 'Client', 'Marketer', 'Job Position'])
        for data in row_data:
            writer.writerow(
                [data.get('ctb'), data.get('round'), data.get('type'), data.get('start'), data.get('consultant'),
                 data.get('client'), data.get('marketer'), data.get('position')]
            )
        file.close()
        file_url = upload_csv_file_s3(file.name)
        return file_url
    except Exception as error:
        write_info(message=f"{error}", function='create_csv_file')


def delete_temp_file(paths):
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
        else:
            write_info(message=f"{path} file does not exist", function='delete_temp_file')


def create_cron_error(job, description):
    try:
        CronError.objects.create(
            description=description,
            job=job
        )
        mail_data = {
            'cc': [], 'bcc': [],
            'to': ['shreyas.k@consultadd.com', 'suman.m@consultadd.com'],
            'body': f'Error :: {description}',
            'subject': f"{job.name} failed at {datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}",
        }
        if os.environ.get('ENV', 'local') == 'prod':
            send_email_without_template(mail_data, 'log1.consultadd@gmail.com')
    except Exception as error:
        write_exception(message=error)


def create_cron_object(name):
    try:
        job, created = CronJob.objects.get_or_create(name=name)
        job.modified = datetime.now()
        job.save()
        return job
    except Exception as error:
        write_exception(message=error)


def get_timezone(city_name):
    try:
        obj = TimezoneFinder()
        geo_locator = Nominatim(user_agent="geoapiExercises")
        location = geo_locator.geocode(city_name)
        result = obj.timezone_at(lat=location.latitude, lng=location.longitude)
        today = datetime.now(tz=timezone(result))
        return today.strftime("%Z")
    except Exception as error:
        write_exception(message=error)
        return None
