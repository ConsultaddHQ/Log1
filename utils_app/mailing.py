from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from log1.utils import write_exception


@shared_task
def send_email(mail_data, from_email, reply_to=None):
    if reply_to is None:
        reply_to = []
    try:
        msg = EmailMultiAlternatives(
            subject=mail_data["subject"],
            from_email=from_email,
            bcc=mail_data["bcc"],
            to=mail_data["to"],
            cc=mail_data["cc"],
            reply_to=reply_to,
            body="body",
        )

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        msg.send()
        return "mail sent"
    except Exception as error:
        write_exception(message=error)
        return error


@shared_task
def send_email_without_template(mail_data, from_email):
    try:
        msg = EmailMultiAlternatives(
            subject=mail_data["subject"],
            body=mail_data["body"],
            from_email=from_email,
            bcc=mail_data["bcc"],
            to=mail_data["to"],
            cc=mail_data["cc"],
        )
        msg.send()
        return "mail sent", True
    except Exception as error:
        write_exception(message=error)
        return error, False


@shared_task
def send_email_attachment_multiple(mail_data, from_email, reply_to=None):
    if reply_to is None:
        reply_to = []
    try:
        msg = EmailMultiAlternatives(
            subject=mail_data["subject"],
            from_email=from_email,
            bcc=mail_data["bcc"],
            to=mail_data["to"],
            cc=mail_data["cc"],
            reply_to=reply_to,
            body="body",
        )

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        for i in mail_data["attachments"]:
            msg.attach_file(i)
        msg.send()
        return "mail sent"
    except Exception as error:
        write_exception(message=error)
        return error
