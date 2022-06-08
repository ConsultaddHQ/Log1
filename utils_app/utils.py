import os
from pytz import timezone
from datetime import datetime
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from utils_app.models import CronJob, CronError
from log1.utils import write_exception, write_info
from utils_app.mailing import send_email_without_template


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
            'to': ['sarang.m@consultadd.com', 'shreyas.k@consultadd.com', 'suman.m@consultadd.com'],
            'body': f'Error :: {description}',
            'subject': f"{job.name} failed at {datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}",
        }
        if os.environ.get('ENV', 'local') == 'prod':
            send_email_without_template(mail_data, 'admin@consultadd.com')
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
