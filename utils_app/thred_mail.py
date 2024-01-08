import csv
import os
import base64
import os.path
import mimetypes
from io import BytesIO
from celery import shared_task
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from django.template.loader import render_to_string

from constance import config
from employee.models import User
from log1.utils import write_exception
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from email.mime import application, multipart, text, base, image, audio

SERVICE_ACCOUNT_FILE = '/home/ubuntu/log1/service.json'
SCOPES = ['https://mail.google.com/', 'https://www.googleapis.com/auth/gmail.readonly']
GROUP_MAIL = [
    'legal@consultadd.com', 'finance@consultadd.com', 'relations@consultadd.com', 'recruitment@consultadd.com',
    'engineering@consultadd.com', 'bbookingg@gmail.com', 'vendormanagement@consultadd.com', 'marketing@consultadd.com'
]


def domain_verification(mail_id):
    if mail_id:
        return False if "@consultadd.com" not in mail_id else True
    else:
        return False


def get_active_user(users):
    active_users = []
    all_active_users = User.objects.filter(is_active=True, account_login=True).values_list('email', flat=True)
    if type(users) is not list:
        return []
    else:
        for user_mail in users:
            if user_mail in GROUP_MAIL:
                continue
            elif not domain_verification(user_mail):
                continue
            elif user_mail not in all_active_users:
                active_users.append(user_mail)
    return active_users


def log_mail_status(status, mail_data, error=None):
    try:
        file = open(config.MAIL_LOGGER, mode="a", newline='')
        mail_logger = csv.writer(file)
        object_id = mail_data.get('object_id', None)
        mail_type = mail_data.get('type', None)
        subject = mail_data.get('subject')
        mail_logger.writerow([
            object_id, mail_type, subject, status, mail_data.get("to"), mail_data.get("cc"), mail_data.get("bcc"),
            error
        ])
    except Exception as e:
        return False, str(e)


# def cred(mail_id, file_dst=None):
#     if os.environ.get('ENV', 'local') != 'prod':
#         mail_id = "shreyas.k@consultadd.com"
#
#     if not mail_id or mail_id == "product@consultadd.com" or not domain_verification(mail_id):
#         mail_id = "shreyas.k@consultadd.com"
#
#     credentials = Credentials.from_service_account_file(
#         filename=SERVICE_ACCOUNT_FILE if file_dst else 'service.json', subject=mail_id, scopes=SCOPES
#     )
#     service = build('gmail', 'v1', credentials=credentials)
#     return service, mail_id


def create_service(mail_id):
    try:
        if os.environ.get('ENV', 'local') != 'prod':
            mail_id = config.DEVELOPER_MAIL

        if not mail_id or mail_id == config.APP_ADMIN or not domain_verification(mail_id):
            mail_id = config.DEVELOPER_MAIL

        credentials = Credentials.from_service_account_file(
            filename=config.GOOGLE_SERVICE_FILE, subject=mail_id, scopes=SCOPES
        )
        service = build('gmail', 'v1', credentials=credentials)
        return service, mail_id
    except Exception as e:
        return False, str(e)


def get_field(email, field_name):
    header = email.get('payload').get('headers')
    for m in header:
        if m['name'] == field_name:
            return m.get('value')


def add_attachments(email, attachments, max_size=int(25)):
    count = 0
    try:
        mime_consumer = {
            'text': text.MIMEText, 'image': image.MIMEImage, 'audio': audio.MIMEAudio
        }
        sz = len(bytes(email))
        for f in attachments:
            margin = max_size * 1024 * 1024 - sz
            if margin <= 100000:
                # Message size limit reached. Added first {count} of {len(attachments)}'
                return True
            mimetype, encoding = mimetypes.guess_type(f)
            if mimetype is None or encoding is not None:
                mimetype = 'application/octet-stream'
            main_type, sub_type = mimetype.split('/', 1)

            consumer = mime_consumer.get(main_type) if (main_type in mime_consumer) else (
                application.MIMEApplication if (main_type == 'application') else None
            )
            if consumer is None:
                # Use the base mimetype
                attachment = base.MIMEBase(main_type, sub_type)
                with open(f, 'rb') as source:
                    attachment.set_payload(source.read())
            else:
                with open(f, 'rb') as source:
                    if sub_type == 'csv':
                        attachment = consumer(source.read().decode('UTF-8'), _subtype=sub_type)
                    else:
                        attachment = consumer(source.read(), _subtype=sub_type)

            # encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(f))
            if len(bytes(attachment)) >= margin:
                continue
            else:
                added = len(bytes(attachment))
                sz += added
                count += 1
                email.attach(attachment)
        return False
    except Exception as e:
        return str(e)


def create_message(from_email, mail_data):
    try:
        body = render_to_string(mail_data.get("template"), mail_data.get("context"))
        body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
                "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        message = MIMEText(body, 'html')
        message['subject'] = mail_data.get("subject")

        if os.environ.get('ENV', 'local') != 'prod':
            from_email = config.DEVELOPER_MAIL

        if from_email in ["suman.m@consultadd.com", "shreyas.k@consultadd.com"]:
            from_email = config.APP_ADMIN

        message['from'] = from_email
        if os.environ.get('ENV', 'local') == 'prod':
            message['to'] = ','.join(get_active_user(mail_data["to"]))
            message['cc'] = ','.join(get_active_user(mail_data["cc"]))
            message['bcc'] = ','.join(get_active_user(mail_data["bcc"]))

        else:
            message['to'] = ','.join(['piyush.y@consultadd.com', 'shreyas.k@consultadd.com', 'gufran.a@consultadd.com'])
            message['cc'] = ''
            message['bcc'] = ''

        b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
        return {'raw': b64_bytes.decode()}
    except Exception as error:
        return {'message': str(error)}


def set_mail_config(to, from_mail, cc, bcc, subject, obj):
    try:
        obj['subject'] = subject
        obj['from'] = from_mail
        if os.environ.get('ENV', 'local') == 'prod':
            obj['to'] = ','.join(get_active_user(to))
            obj['cc'] = ','.join(get_active_user(cc))
            obj['bcc'] = ','.join(get_active_user(bcc))
        else:
            obj['cc'] = ''
            obj['bcc'] = ''
            obj['to'] = ','.join(
                ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com', 'gufran.a@consultadd.com']
            )
        return obj, None
    except Exception as error:
        return None, str(error)


def create_mail_body(mail_obj, mail_data, from_email, request=None):
    try:
        if mail_data.get("template"):
            body = render_to_string(mail_data.get("template"), mail_data.get("context"))
            body = body.replace(
                "\\r\\n", "<br>").replace(";newline;", "<br>").replace("\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        else:
            body = mail_data.get('body')
        message = MIMEText(body, 'html')
        subject = get_field(mail_obj, 'subject')
        message, error = set_mail_config(
            mail_data.get("to"), from_email, mail_data.get("cc"), mail_data.get("bcc"), subject, message
        )
        if error:
            write_exception(error, request)
            return None, error
        message['In-Reply-To'] = get_field(mail_obj, 'Message-Id')
        message['References'] = get_field(mail_obj, 'Message-Id')
        email_body = {
            'message': {
                'threadId': mail_obj.get('threadId'),
                'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()
            }
        }
        return email_body, None
    except Exception as error:
        write_exception(error, request)
        return None, str(error)


def execute_mail(service, mail_body, draft=False, media=None):
    try:
        retry = 0
        while retry < int(config.EMAIL_MAX_RETRY):
            if draft:
                if media:
                    draft = service.users().drafts().create(userId='me', body=mail_body, media_body=media).execute()
                else:
                    draft = service.users().drafts().create(userId='me', body=mail_body).execute()
                message = service.users().drafts().send(userId='me', body={'id': draft['id']}).execute()
            else:
                message = (service.users().messages().send(userId="me", body=mail_body).execute())
            if 'SENT' in message.get('labelIds'):
                return message, True
            retry += 1
            return "execution failed", False
    except Exception as error:
        return str(error), False


@shared_task
def send_mail_in_thread(mail_data, from_email, request, mail_id):
    try:
        _from_email = from_email
        from_email = config.APP_ADMIN
        service, from_mail = create_service(from_email)
        if not service:
            log_mail_status("Not Sent", mail_data, "issue while creating service object")
            return None, False, None

        try:
            mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()
        except Exception:
            if _from_email:
                service, from_mail = create_service(_from_email)
                if not service:
                    log_mail_status("Not Sent", mail_data, "issue while creating service object")
                    return None, False, None
                mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()
            else:
                service, from_mail = create_service(config.APP_ADMIN)
                return send_mail_without_thread(mail_data, service, request)

        email_body, error = create_mail_body(mail_obj, mail_data, from_mail, request)
        if error:
            log_mail_status("Not Sent", mail_data, error)
            return error, False, None
        message, status = execute_mail(service, email_body, True)
        if status:
            log_mail_status("Sent", mail_data)
            return message.get('id'), True, from_mail
        else:
            write_exception(message=message, request=request)
            log_mail_status("Not Sent", mail_data, message)
            return message, False, from_mail
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error), False, None


@shared_task
def send_email(mail_data, from_email, request=None, cron_execution=None):
    try:
        retry = 0
        service, from_mail = create_service(from_email)
        if not service:
            log_mail_status("Not Sent", mail_data, from_mail)
            return None, False, None

        msg_resp = create_message(from_mail, mail_data)
        if 'message' in msg_resp.keys():
            write_exception(message=msg_resp.get('message'), request=request)
            return msg_resp.get('message'), False, None

        while retry < int(config.EMAIL_MAX_RETRY):
            try:
                message = (service.users().messages().send(userId="me", body=msg_resp).execute())
            except Exception:
                service, from_mail = create_service(config.APP_ADMIN)
                msg = create_message(from_mail, mail_data)
                message = (service.users().messages().send(userId="me", body=msg).execute())
            if 'SENT' in message.get('labelIds'):
                log_mail_status("SENT", mail_data)
                return message.get('id'), True, from_mail
            retry += 1
        log_mail_status("Not Sent", mail_data)
        return None, False, None
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error), False, None


@shared_task
def send_email_without_template(mail_data, from_email, request=None, mail_id=None, cron_execution=None):
    try:
        service, from_mail = create_service(from_email)
        if not service:
            log_mail_status("Not Sent", mail_data, "issue while creating service object")
            return None, False, None
        if mail_id:
            try:
                mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()
            except Exception:
                service, from_mail = create_service(config.APP_ADMIN)
                mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()

            email_body, error = create_mail_body(mail_obj, mail_data, from_mail, request)
            if error:
                log_mail_status("Not Sent", mail_data, error)
                return error, False, None
            message, status = execute_mail(service, email_body, True)
            if status:
                log_mail_status("Sent", mail_data)
                return message.get('id'), True, from_mail
            else:
                write_exception(message=message, request=request)
                log_mail_status("Not Sent", mail_data, message)
                return message, False, from_mail
        else:
            message = MIMEText(mail_data.get("body"), 'html')
            message, error = set_mail_config(
                mail_data.get("to"), config.APP_ADMIN, mail_data.get("cc"),
                mail_data.get("bcc"), mail_data.get("subject"), message
            )
            if error:
                write_exception(error, request)
                return None, error
            b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
            message, status = execute_mail(service, {'raw': b64_bytes.decode()}, False)
            if status:
                log_mail_status("Sent", mail_data)
                return message.get('id'), True, from_mail
            else:
                write_exception(message=message, request=request)
                log_mail_status("Not Sent", mail_data, message)
                return message, False, from_mail
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error), False, None


def send_mail_without_thread(mail_data, service, request=None):
    try:
        from_email = config.APP_ADMIN
        message = MIMEText(mail_data.get("body"), 'html')
        message, error = set_mail_config(
            mail_data.get("to"), from_email, mail_data.get("cc"),
            mail_data.get("bcc"), mail_data.get("subject"), message
        )
        if error:
            log_mail_status("Not Sent", mail_data, error)
            write_exception(error, request)
            return None, error

        body = render_to_string(mail_data.get("template"), mail_data.get("context"))
        body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        message.attach(MIMEText(body, 'html'))

        file_size = False
        if len(mail_data["attachments"]) > 0:
            file_size = add_attachments(message, mail_data["attachments"])

        if file_size:
            write_exception(str("Email size is more then 25 MB"), request)
            return str("Email size is more then 25 MB"), False, None

        media = MediaIoBaseUpload(BytesIO(message.as_bytes()), mimetype='message/rfc822', resumable=True)
        message, status = execute_mail(service, media, False)
        if status:
            log_mail_status("Sent", mail_data)
            return message.get('id'), True, from_email
        else:
            write_exception(message=message, request=request)
            log_mail_status("Not Sent", mail_data, message)
            return message, False, from_email
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error), False, ""


@shared_task
def send_email_attachment_multiple(mail_data, from_email, request=None, mail_id=None, reply_to=None, cron_execution=None):
    try:
        _from_email = from_email
        from_email = config.APP_ADMIN
        service, from_mail = create_service(from_email)
        if not service:
            log_mail_status("Not Sent", mail_data, "issue while creating service object")
            return None, False, None

        if mail_id:
            try:
                mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()
            except Exception:
                if _from_email:
                    service, from_mail = create_service(_from_email)
                    mail_obj = service.users().messages().get(userId='me', id=mail_id).execute()
                else:
                    service, from_mail = create_service(config.APP_ADMIN)
                    return send_mail_without_thread(mail_data, service, request)

            message = multipart.MIMEMultipart()
            subject = get_field(mail_obj, 'subject')
            message, error = set_mail_config(
                mail_data.get("to"), from_email, mail_data.get("cc"), mail_data.get("bcc"), subject, message
            )

            if from_email in ["suman.m@consultadd.com", "shreyas.k@consultadd.com"]:
                message['from'] = 'product@consultadd.com'
            message['In-Reply-To'] = get_field(mail_obj, 'Message-Id')
            message['References'] = get_field(mail_obj, 'Message-Id')

            body = render_to_string(mail_data["template"], mail_data["context"])
            body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
                "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
            message.attach(MIMEText(body,'html'))

            file_size = False
            if len(mail_data["attachments"]) > 0:
                file_size = add_attachments(message, mail_data["attachments"])

            if file_size:
                log_mail_status("Not Sent", mail_data, "Email size is more then 25 MB")
                write_exception("Email size is more then 25 MB", request)
                return "Email size is more then 25 MB", False, None

            media = MediaIoBaseUpload(BytesIO(message.as_bytes()), mimetype='message/rfc822', resumable=True)
            email_body = {
                'message': {
                    'threadId': mail_obj.get('threadId')
                }
            }
            message, status = execute_mail(service, email_body, True, media)
            if status:
                log_mail_status("Sent", mail_data)
                return message.get('id'), True, from_email
            else:
                write_exception(message=message, request=request)
                log_mail_status("Not Sent", mail_data, message)
                return message, False, from_email
        else:
            return send_mail_without_thread(mail_data, service, request)
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error), False, None
