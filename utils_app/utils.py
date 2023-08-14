import os
import csv
import boto3
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pytz import timezone
from datetime import datetime
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from utils_app.models import CronJob, CronError
from log1.utils import write_exception, write_info
from utils_app.mailing import send_email_without_template

TECHNOLOGIES = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps', 'BA', 'DA',
                'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce', 'Cyber Security', 'Other']


def generate_s3_url(filename):
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


def export_to_csv(payload, columns, filename, request=None):
    try:
        file = open(filename, 'w')
        writer = csv.writer(file)
        column_name = [column['name'] for column in columns]
        writer.writerow([column['display_name'] for column in columns])
        for data in payload:
            row_elems = []
            for i in range(0, len(column_name)):
                if data[column_name[i]] and type(data[column_name[i]]) == list:
                    if None in data[column_name[i]]:
                        data[column_name[i]].remove(None)
                    elif not data[column_name[i]]:
                        data[column_name[i]] = None
                    row_elems.append(", ".join(elem for elem in data[column_name[i]]))
                else:
                    row_elems.append(data[column_name[i]])
            writer.writerow(row_elems)
        file.close()
        file_url = generate_s3_url(file.name)
        return file_url
    except Exception as error:
        write_exception(error, request)
        return ""


def generate_swagger_auto_schema(query_params=[], body_params=[], responses={}, methods=[]):
    def decorator(view_func):
        query_parameters = []
        if len(query_params):
            for param_details in query_params:
                parameter = openapi.Parameter(
                    param_details['name'],
                    openapi.IN_QUERY,
                    description=param_details['description'],
                    type=param_details['type'],
                    required=param_details.get('required', False)
                )
                query_parameters.append(parameter)

        request_body_schema = None
        if len(body_params):
            body_parameters = {}
            for param_name, param_schema in body_params[0].items():
                body_parameters[param_name] = param_schema

            request_body_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=body_parameters,
                required=body_params[1] if len(body_params[1]) else []
            )

        if len(responses):
            swagger_responses = {}
            for status_code, data in responses.items():
                response = openapi.Response(
                    description=data.get('description'),
                    examples={
                        'application/json': data.get('response')
                    }
                )
                swagger_responses[status_code] = response

        decorated_view = swagger_auto_schema(
            manual_parameters=query_parameters,
            request_body=request_body_schema,
            responses=swagger_responses,
            methods=methods
        )(view_func)

        return decorated_view

    return decorator
