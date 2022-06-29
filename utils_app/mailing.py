import os
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from log1.utils import write_exception, write_info


@shared_task
def send_email(mail_data, from_email, reply_to=None, request=None):
    if os.environ.get('ENV', 'local') == 'prod':
        to = mail_data["to"]
        cc = mail_data["cc"]
        bcc = mail_data["bcc"]
    else:
        cc, bcc = [], []
        to = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']

    if reply_to is None:
        reply_to = []
    try:
        msg = EmailMultiAlternatives(
            body="body",
            reply_to=reply_to,
            to=to, cc=cc, bcc=bcc,
            from_email=from_email,
            subject=mail_data["subject"],
        )

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        msg.send()
        return "mail sent", True
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False


@shared_task
def send_email_without_template(mail_data, from_email, request=None):
    try:
        if os.environ.get('ENV', 'local') == 'prod':
            to = mail_data["to"]
            cc = mail_data["cc"]
            bcc = mail_data["bcc"]
        else:
            cc, bcc = [], []
            to = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']

        msg = EmailMultiAlternatives(
            to=to, cc=cc, bcc=bcc,
            from_email=from_email,
            body=mail_data["body"],
            subject=mail_data["subject"],
        )
        msg.send()
        return "mail sent", True
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['body']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_without_template', request=request)
        return str(error), False


@shared_task
def send_email_attachment_multiple(mail_data, from_email, reply_to=None, request=None):
    if os.environ.get('ENV', 'local') == 'prod':
        to = mail_data["to"]
        cc = mail_data["cc"]
        bcc = mail_data["bcc"]
    else:
        cc, bcc = [], []
        to = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']

    if reply_to is None:
        reply_to = []
    try:
        msg = EmailMultiAlternatives(
            body="body",
            reply_to=reply_to,
            from_email=from_email,
            to=to, cc=cc, bcc=bcc,
            subject=mail_data["subject"],
        )

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        for i in mail_data["attachments"]:
            msg.attach_file(i)
        msg.send()
        return "mail sent", True
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_attachment_multiple', request=request)
        return str(error), False
