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


def get_attachment_status(project):
    start_date = 1 if project.start_date else 0
    client_address, vendor_address, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0

    if project.attachments.filter(attachment_type='msa_signed'):
        s_msa = 1

    if project.attachments.filter(attachment_type='work_order_signed'):
        s_work_order = 1

    if project.attachments.filter(attachment_type='work_order_msa_signed'):
        s_msa, s_work_order = 1, 1

    if project.client_address and len(project.client_address.strip()) > 0:
        client_address = 1

    if project.vendor_address and len(project.vendor_address.strip()) > 0:
        vendor_address = 1

    if project.reporting_details and len(project.reporting_details.strip()) > 0:
        reporting_details = 1

    total = s_msa + s_work_order + client_address + vendor_address + start_date + reporting_details
    list_status = True if (total / 6) >= 1 else False
    return {
        "total": 6,
        "msa_signed": s_msa,
        "status": list_status,
        "start_date": start_date,
        "client_address": client_address,
        "vendor_address": vendor_address,
        "work_order_signed": s_work_order,
        "reporting_details": reporting_details,
    }


def get_project_check_list(project):
    msa, work_order = 0, 0

    if project.attachments.filter(attachment_type='msa'):
        msa = 1

    if project.attachments.filter(attachment_type='work_order'):
        work_order = 1

    if project.attachments.filter(attachment_type='work_order_msa'):
        msa, work_order = 1, 1

    result = get_attachment_status(project)

    return {
        "total": 6,
        "msa": msa,
        "work_order": work_order,
        "status": result["status"],
        "msa_signed": result["s_msa"],
        "start_date": result["start_date"],
        "client_address": result["client_address"],
        "vendor_address": result["vendor_address"],
        "work_order_signed": result["s_work_order"],
        "reporting_details": result["reporting_details"],
    }
