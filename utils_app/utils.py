import os
import csv
import ssl

import boto3
import certifi
from pytz import timezone
from constance import config
from datetime import datetime
from slack_sdk import WebClient
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from utils_app.models import CronJob, CronError
from tracking.models import ExportData, Devices
from log1.utils import write_exception, write_info
from utils_app.thred_mail import send_email_without_template as _send_email_without_template

TECHNOLOGIES = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps', 'BA', 'DA',
                'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce', 'Cyber Security', 'Other']


def add_export_log(export_type, request):
    try:
        cookie_value = request.META.get('HTTP_X_ID_TOKEN', None)
        devices_cookies = Devices.objects.filter(cookies_value=cookie_value).first()
        if devices_cookies:
            ExportData.objects.create(
                name=export_type,
                device=devices_cookies
            )
    except Exception as error:
        write_exception(message=error, request=request)


def generate_s3_url(filename, request=None, export_type=None):
    try:
        if request:
            add_export_log(export_type, request)
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
        writer.writerow(['Consultant', 'Marketer', 'Recruiter', 'Days', 'Team', 'Skills', 'Open Offer Count'])
        for data in row_data:
            writer.writerow(
                [data.get('consultant'), data.get('marketer'), data.get('recruiter'), data.get('days'),
                 data.get('team'), data.get('skills'), data.get('open_offer'), data.get('position')]
            )
        file.close()
        file_url = generate_s3_url(file.name)
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
            'to': ['shreyas.k@consultadd.com'],
            'body': f'Error :: {description}',
            'subject': f"{job.name} failed at {datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}",
        }
        if os.environ.get('ENV', 'local') == 'prod':
            _send_email_without_template(mail_data, 'product@consultadd.com')
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


def export_to_csv(payload, columns, filename, request=None, report_type=None):
    try:
        file = open(filename, 'w')
        writer = csv.writer(file)
        column_name = [column['name'] for column in columns]
        writer.writerow([column['display_name'] for column in columns])
        for data in payload:
            row_elems = []
            for i in range(0, len(column_name)):
                column_value = data.get(column_name[i], None)
                if column_value:
                    if data[column_name[i]] and type(data[column_name[i]]) == list:
                        if None in data[column_name[i]]:
                            data[column_name[i]].remove(None)
                        elif not data[column_name[i]]:
                            data[column_name[i]] = None
                        row_elems.append(", ".join(elem for elem in data[column_name[i]]))
                    else:
                        row_elems.append(data[column_name[i]])
                else:
                     row_elems.append('')
            writer.writerow(row_elems)
        file.close()
        file_url = generate_s3_url(file.name, request, report_type)
        return file_url
    except Exception as error:
        write_exception(error, request)
        return ""


def set_member_id(user_obj: any, member_id: int, request: any = None) -> str:
    try:
        user_obj.slack_id = member_id
        user_obj.save()
    except Exception as error:
        write_exception(error, request)


def get_slack_id(user_obj: any, request: any = None) -> str:
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        client = WebClient(token=config.SLACK_TOKEN, ssl=ssl_context)
        response = client.users_lookupByEmail(email=user_obj.email)
        member_id = response.get('user', {}).get('id')
        set_member_id(user_obj, member_id, request)
        return member_id
    except Exception as error:
        write_exception(error, request)
        return None


def get_slack_tag(user_obj: any, request: any = None) -> str:
    try:
        if not user_obj:
            return "Not Available"

        slack_id = user_obj.slack_id if user_obj.slack_id else get_slack_id(user_obj, request)

        if slack_id:
            return f"<@{slack_id}>"

        return user_obj.employee_name
    except Exception as error:
        write_exception(error, request)
        return user_obj.employee_name
