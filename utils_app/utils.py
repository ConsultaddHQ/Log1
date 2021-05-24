from datetime import datetime

from log1.utils import write_exception
from utils_app.models import CronJob, CronError
from utils_app.mailing import send_email_without_template


def create_cron_error(job, description):
    try:
        CronError.objects.create(
            description=description,
            job=job
        )
        mail_data = {
            'cc': [],
            'bcc': [],
            'to': ['sarang.m@consultadd.com', 'devesh.n@consultadd.com'],
            'body': f'Error :: {description}',
            'subject': f"{job.name} failed at {datetime.now().strftime('%d-%B-%Y::%H:%M:%S')}",
        }
        send_email_without_template(mail_data, 'admin@log1.com')
    except Exception as error:
        write_exception(message=error, class_name=None, function_name='create_cron_error')


def create_cron_object(name):
    job, created = CronJob.objects.get_or_create(name=name)
    job.modified = datetime.now()
    job.save()
    return job
