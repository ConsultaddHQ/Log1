import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from log1.utils import write_exception, write_info
import base64


SCOPES = ['https://mail.google.com/','https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']


def cred():
    creds = None
    if os.path.exists('mailtoken.json'):
        creds = Credentials.from_authorized_user_file('mailtoken.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'mailkey.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('mailtoken.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service


def get_field(email, field_name):
    header = email['payload']['headers']
    for m in header:
        if m['name'] == field_name:
            return m['value']   
        

def create_message(from_email, mail_data):
    body = render_to_string(mail_data["template"], mail_data["context"])
    body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
    message = MIMEText(body, 'html')
    message['subject'] = mail_data["subject"]
    message['from'] = from_email
    if os.environ.get('ENV', 'local') == 'prod':
        message['to'] = mail_data["to"]
        message['cc'] = mail_data["cc"]
        message['bcc'] = mail_data["bcc"]
        
    else:
        message['to'] = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']
        message['cc'] = []
        message['bcc'] = []

    return {'raw': base64.urlsafe_b64encode(message.as_string())}


@shared_task
def send_mail_in_thread(mail_data, mail_id, from_email, reply_to=None, request=None):
    service = cred()
    email_data = service.users().messages().get(userId='me', id=mail_id).execute()

    body = render_to_string(mail_data["template"], mail_data["context"])
    body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
    message = MIMEText(body, 'html')
    message['to'] = mail_data["to"]
    message['from'] = from_email
    message['subject'] = get_field(email_data, 'subject')
    message['In-Reply-To'] = get_field(email_data, 'Message-Id')
    message['References'] = get_field(email_data, 'Message-Id')

    if os.environ.get('ENV', 'local') == 'prod':
        message['to'] = mail_data["to"]
        message['cc'] = mail_data["cc"]
        message['bcc'] = mail_data["bcc"]
        
    else:
        message['to'] = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']
        message['cc'] = []
        message['bcc'] = []
        
    email_body = {'message' : {'threadId' : email_data['threadId'], 'raw' : base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode()}}
    service = cred()
    draft = service.users().drafts().create(userId='me', body=email_body).execute()
    message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
    return message['id'], True    



@shared_task
def send_email(mail_data, from_email, reply_to=None, request=None):
    try:
        msg = create_message(from_email, mail_data)
        service = cred()
        message = (service.users().messages().send(userId="me", body=msg).execute())
        return message['id'], True
    
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False


@shared_task
def send_email_without_template(mail_data, from_email, request=None):
    try:
        message = MIMEText(mail_data["body"])
        message['subject'] = mail_data["subject"]
        message['from'] = from_email
        if os.environ.get('ENV', 'local') == 'prod':
            message['to'] = mail_data["to"]
            message['cc'] = mail_data["cc"]
            message['bcc'] = mail_data["bcc"]
            
        else:
            message['to'] = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']
            message['cc'] = []
            message['bcc'] = []
        service = cred()
        message = (service.users().messages().send(userId="me", body={'raw': base64.urlsafe_b64encode(message.as_string())}).execute())
        return message['id'], True

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
    breakpoint()
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
