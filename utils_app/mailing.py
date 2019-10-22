import logging
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


@shared_task
def send_email(mail_data, from_email, reply_to=[]):
    try:
        msg = EmailMultiAlternatives(subject=mail_data["subject"], body="body", from_email=from_email,
                                     to=mail_data["to"], cc=mail_data["cc"], bcc=mail_data["bcc"], reply_to=reply_to)

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace(
            "\\r\\n", "<br>").replace(
            ";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        msg.send()
        return "mail sent"
    except Exception as error:
        logger.error(error)
        return error


@shared_task
def send_email_attachment_multiple(mail_data, from_email, reply_to=[]):
    try:
        msg = EmailMultiAlternatives(subject=mail_data["subject"], body="body", from_email=from_email,
                                     to=mail_data["to"], cc=mail_data["cc"], bcc=mail_data["bcc"], reply_to=reply_to)

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace(
            "\\n", "<br>").replace(
            ";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        msg.attach_alternative(body, 'text/html')
        for i in mail_data["attachments"]:
            msg.attach_file(i)
        msg.send()
        return "mail sent"
    except Exception as error:
        logger.error(error)
        return error
