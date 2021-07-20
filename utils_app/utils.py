import os
from datetime import datetime

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
            'to': ['sarang.m@consultadd.com'],
            'body': f'Error :: {description}',
            'subject': f"{job.name} failed at {datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}",
        }
        send_email_without_template(mail_data, 'admin@log1.com')
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
