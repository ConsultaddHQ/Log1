import os
import base64
import os.path
from email import encoders
from celery import shared_task
from email.mime.text import MIMEText
from email.mime import multipart, base
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
# from google.auth.transport.requests import Request
from log1.utils import write_exception, write_info
from django.template.loader import render_to_string
# from google_auth_oauthlib.flow import InstalledAppFlow

# SCOPES = ['https://mail.google.com/','https://www.googleapis.com/auth/gmail.readonly']
SERVICE_ACCOUNT_FILE = 'service.json'
SCOPES = ['https://mail.google.com/']

def cred(mail_id):
    if os.environ.get('ENV', 'local') != 'prod':
        mail_id="suman.m@consultadd.com"
        
    credentials = Credentials.from_service_account_file(
        filename=SERVICE_ACCOUNT_FILE,
        scopes = SCOPES,
        subject=mail_id,
    )
    service = build('gmail', 'v1', credentials=credentials)
    return service


def get_field(email, field_name):
    header = email['payload']['headers']
    for m in header:
        if m['name'] == field_name:
            return m['value']   


def add_file(filepath, filename, object):
    attachment = open(filepath, "rb")
    p = base.MIMEBase('application', 'octet-stream')
    p.set_payload((attachment).read())
    encoders.encode_base64(p)
    p.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    object.attach(p)
    return object        


def create_message(from_email, mail_data):
    body = render_to_string(mail_data["template"], mail_data["context"])
    body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
    message = MIMEText(body, 'html')
    message['subject'] = mail_data["subject"]
    message['from'] = from_email
    if os.environ.get('ENV', 'local') == 'prod':
        message['to'] = ','.join(mail_data["to"])
        message['cc'] = ','.join(mail_data["cc"])
        message['bcc'] = ','.join(mail_data["bcc"])
        
    else:
        message['to'] = ','.join(['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com'])
        message['cc'] = ''
        message['bcc'] = ''

    return {'raw': base64.urlsafe_b64encode(message.as_string())}


def set_mail_config(to, from_mail, cc, bcc, subject, object):
    breakpoint()
    
    object['subject'] = subject
    if os.environ.get('ENV', 'local') == 'prod':
        object['to'] = ','.join(to)
        object['cc'] = ','.join(cc)
        object['bcc'] = ','.join(bcc)
        object['from'] = from_mail
    else:
        object['from'] = "suman.m@consultadd.com"
        object['cc'] = ''
        object['bcc'] = ''      
        object['to'] = ','.join(['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com'])
    return object


@shared_task
def send_mail_in_thread(mail_data, mail_id, from_email, reply_to=None, request=None):
    try:
        service = cred(from_email)
        email_data = service.users().messages().get(userId='me', id=mail_id).execute()

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
                "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
        message = MIMEText(body, 'html')
        subject = get_field(email_data, 'subject')
        message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message) 
        message['In-Reply-To'] = get_field(email_data, 'Message-Id')
        message['References'] = get_field(email_data, 'Message-Id')
        email_body = {'message' : {'threadId' : email_data['threadId'], 'raw' : base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode()}}
        draft = service.users().drafts().create(userId='me', body=email_body).execute()
        message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
        return message['id'], True   
     
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False


@shared_task
def send_email(mail_data, from_email, reply_to=None, request=None):
    try:
        msg = create_message(from_email, mail_data)
        service = cred(from_email)
        message = (service.users().messages().send(userId="me", body=msg).execute())
        return message['id'], True
    
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False


@shared_task
def send_email_without_template(mail_data, from_email, request=None, mail_id=None):
    try:
        service = cred(from_email)
        if mail_id:
            email_data = service.users().messages().get(userId='me', id=mail_id).execute()  
            message = MIMEText(mail_data["body"])
            subject = get_field(email_data, 'subject')
            message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message) 
            message['In-Reply-To'] = get_field(email_data, 'Message-Id')
            message['References'] = get_field(email_data, 'Message-Id')
            email_body = {'message' : {'threadId' : email_data['threadId'], 'raw' : base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode()}}
            draft = service.users().drafts().create(userId='me', body=email_body).execute()
            message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
            return message['id'], True
        else:
            message = MIMEText(mail_data["body"])
            subject = mail_data["subject"]
            message['from'] = from_email
            message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message) 
            message = (service.users().messages().send(userId="me", body={'raw': base64.urlsafe_b64encode(message.as_string())}).execute())
            return message['id'], True

    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['body']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_without_template', request=request)
        return str(error), False


@shared_task
def send_email_attachment_multiple(mail_data, from_email, request=None, mail_id=None, reply_to=None):
    try:
        breakpoint()
        service = cred(from_email)
        if mail_id is not None:
            email_data = service.users().messages().get(userId='me', id=mail_id).execute()  
            message = multipart.MIMEMultipart()

            subject = get_field(email_data, 'subject')
            message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message)            
            message['In-Reply-To'] = get_field(email_data, 'Message-Id')
            message['References'] = get_field(email_data, 'Message-Id')

            if reply_to is None:
                body = render_to_string(mail_data["template"], mail_data["context"])
                body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
                    "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
                message.attach(MIMEText(body,'html'))
                
                for i in mail_data["attachments"]:
                    filename = i.split('/')[2]
                    message = add_file(i, filename, message)
    
                b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
                b64_string = b64_bytes.decode()
        
            email_body = {'message' : {'threadId' : email_data['threadId'], 'raw' : b64_string}}
            draft = service.users().drafts().create(userId='me', body=email_body).execute()
            message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
            return message['id'], True
        else:
            message = multipart.MIMEMultipart()
            message['from'] = from_email
            subject = mail_data["subject"]
            message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message) 
            
            if reply_to is None:
                body = render_to_string(mail_data["template"], mail_data["context"])
                body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
                    "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
                message.attach(MIMEText(body,'html'))
                
                for i in mail_data["attachments"]:
                    filename = i.split('/')[2]
                    message = add_file(i, filename, message)
    
                b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
                b64_string = b64_bytes.decode()
                message = (service.users().messages().send(userId="me", body={'raw':b64_string}).execute())
                return message['id'], True
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_attachment_multiple', request=request)
        return str(error), False
