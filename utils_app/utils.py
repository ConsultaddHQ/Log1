from datetime import datetime
from utils_app.models import CronError
from utils_app.mailing import send_email_without_template


def create_cron_error(job, description):
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
