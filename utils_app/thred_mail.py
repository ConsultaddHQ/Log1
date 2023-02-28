import os
import base64
import os.path
import mimetypes
from io import BytesIO
from email import encoders
from celery import shared_task
from email.mime.text import MIMEText
from email.mime import multipart, base
from googleapiclient.discovery import build
from log1.utils import write_exception, write_info
from googleapiclient.http import MediaIoBaseUpload
from django.template.loader import render_to_string
# from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from email.mime import application, multipart, text, base, image, audio
# from google_auth_oauthlib.flow import InstalledAppFlow
# SCOPES = ['https://mail.google.com/','https://www.googleapis.com/auth/gmail.readonly']
# SERVICE_ACCOUNT_FILE = 'service.json'
SCOPES = ['https://mail.google.com/']


def cred(mail_id):
    if os.environ.get('ENV', 'local') != 'prod':
        mail_id = "suman.m@consultadd.com"
        
    if mail_id == "product@consultadd.com":
        mail_id = "suman.m@consultadd.com"

    credentials = Credentials.from_service_account_file(
        filename="service.json",
        scopes=SCOPES,
        subject=mail_id,
    )
    service = build('gmail', 'v1', credentials=credentials)
    return service, mail_id 


def get_field(email, field_name):
    header = email['payload']['headers']
    for m in header:
        if m['name'] == field_name:
            return m['value']   


def add_attachments(email, attachments, max_MB= int(25)):
    mime_consumer = {
        'text': text.MIMEText, 'image': image.MIMEImage, 'audio': audio.MIMEAudio
    }

    sz = len(bytes(email))
    count = 0
    for f in attachments:
        print(sz / 1024 / 1024)
        margin = max_MB * 1024 * 1024 - sz
        if margin <= 100000:
            # Message size limit reached. Added first {count} of {len(attachments)}'
            break
        mimetype, encoding = mimetypes.guess_type(f)
        if mimetype is None or encoding is not None:
            mimetype = 'application/octet-stream'
        main_type, sub_type = mimetype.split('/', 1)

        consumer = mime_consumer[main_type] if (main_type in mime_consumer) else (
            application.MIMEApplication if (main_type == 'application') else None
        )
        attachment = None
        if consumer is None:
            # Use the base mimetype
            attachment = base.MIMEBase(main_type, sub_type)
            with open(f, 'rb') as source:
                attachment.set_payload(source.read())
        else:
            # Use the known conversion.
            print(f'Reading file of type {main_type}')
            with open(f, 'rb') as source:
                if sub_type == 'csv':
                    attachment = consumer(source.read().decode('UTF-8'), _subtype=sub_type)
                else:
                    attachment = consumer(source.read(), _subtype=sub_type)

        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(f))
        if len(bytes(attachment)) >= margin:
            # Add your own "skip this file" or "these should be links from Drive" logic.
            margin = 0
            return True
        else:
            added = len(bytes(attachment))
            sz += added
            count += 1
            email.attach(attachment)
            return False
    # print(f'Email size is now ~{len(bytes(email)) / 1024 / 1024} MB')


# def add_file(filepath, filename, object):
#     attachment = open(filepath, "rb")
#     p = base.MIMEBase('application', 'octet-stream')
#     p.set_payload(attachment.read())
#     encoders.encode_base64(p)
#     p.add_header('Content-Disposition', "attachment; filename= %s" % filename)
#     object.attach(p)
#     return object        

def create_message(from_email, mail_data):
    body = render_to_string(mail_data["template"], mail_data["context"])
    body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
            "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
    message = MIMEText(body, 'html')
    message['subject'] = mail_data["subject"]
    
    if os.environ.get('ENV', 'local') != 'prod':
        from_email = "suman.m@consultadd.com"
        
    if from_email == "suman.m@consultadd.com":
        from_email="product@consultadd.com"
        
    message['from'] = from_email
    if os.environ.get('ENV', 'local') == 'prod':
        message['to'] = ','.join(mail_data["to"])
        message['cc'] = ','.join(mail_data["cc"])
        message['bcc'] = ','.join(mail_data["bcc"])
        
    else:
        message['to'] = ','.join(['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com'])
        message['cc'] = ''
        message['bcc'] = ''
        
    b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': b64_bytes.decode()}


def set_mail_config(to, from_mail, cc, bcc, subject, obj):
    obj['subject'] = subject
    obj['from'] = from_mail
    if os.environ.get('ENV', 'local') == 'prod':
        obj['to'] = ','.join(to)
        obj['cc'] = ','.join(cc)
        obj['bcc'] = ','.join(bcc)
    else:
        obj['cc'] = ''
        obj['bcc'] = ''
        obj['to'] = ','.join(
            ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com', 'gufran.a@consultadd.com']
        )
    return obj


@shared_task
def send_mail_in_thread(mail_data, from_email, request, mail_id):
    try:
        from_email = "product@consultadd.com"
        service, from_mail_id = cred(from_email)
        email_data = service.users().messages().get(userId='me', id=mail_id).execute()

        body = render_to_string(mail_data["template"], mail_data["context"])
        body = body.replace("\\r\\n", "<br>").replace(";newline;", "<br>").replace(
                "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")    
        message = MIMEText(body, 'html')
        subject = get_field(email_data, 'subject')
        message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message) 
        message['In-Reply-To'] = get_field(email_data, 'Message-Id')
        message['References'] = get_field(email_data, 'Message-Id')
        email_body = {'message' : {'threadId' : email_data['threadId'], 'raw' : base64.urlsafe_b64encode(message.as_bytes()).decode()}}
        draft = service.users().drafts().create(userId='me', body=email_body).execute()
        message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
        return message['id'], True, from_mail_id   
     
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False, None


@shared_task
def send_email(mail_data, from_email, request=None):
    try:
        from_email = "product@consultadd.com"
        service, from_mail_id = cred(from_email)
        msg = create_message(from_mail_id, mail_data)
        message = (service.users().messages().send(userId="me", body=msg).execute())
        return message['id'], True, from_mail_id
    
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email', request=request)
        return str(error), False, None


@shared_task
def send_email_without_template(mail_data, from_email, request=None, mail_id=None):
    try:
        from_email = "product@consultadd.com"
        service, from_mail_id = cred(from_email)
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
            return message['id'], True, from_mail_id
        else:
            message = MIMEText(mail_data["body"],'html')
            message['subject'] = mail_data["subject"]
            if os.environ.get('ENV', 'local') == 'prod':
                message['to'] = ','.join(mail_data["to"])
                message['cc'] = ','.join(mail_data["cc"])
                message['bcc'] = ','.join(mail_data["bcc"])
                
            else:
                message['to'] = ','.join(
                    ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com', 'gufran.a@consultadd.com']
                )
                message['cc'] = ''
                message['bcc'] = ''
            message['from'] = 'product@consultadd.com'
            b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
            message = (service.users().messages().send(userId="me", body={'raw': b64_bytes.decode()}).execute())
            return message['id'], True, from_mail_id

    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['body']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_without_template', request=request)
        return str(error), False, None


@shared_task
def send_email_attachment_multiple(mail_data, from_email, request=None, mail_id=None, reply_to=None):
    try:
        from_email = "product@consultadd.com"
        service, from_mail_id = cred(from_email)
        if mail_id is not None:
            email_data = service.users().messages().get(userId='me', id=mail_id).execute()  
            message = multipart.MIMEMultipart()

            subject = get_field(email_data, 'subject')
            message = set_mail_config(mail_data["to"], from_email, mail_data["cc"], mail_data["bcc"], subject, message)
            if from_email == "suman.m@consultadd.com": 
                message['from'] = 'product@consultadd.com'
            message['In-Reply-To'] = get_field(email_data, 'Message-Id')
            message['References'] = get_field(email_data, 'Message-Id')

            if reply_to is None:
                body = render_to_string(mail_data["template"], mail_data["context"])
                body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
                    "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
                message.attach(MIMEText(body,'html'))
                
                file_size = False
                if len(mail_data["attachments"]) > 0:
                    file_size = add_attachments(message,mail_data["attachments"])
                    
                if file_size:
                    return str("Email size is more then 25 MB"), False, None
                
                # for i in mail_data["attachments"]:
                #     filename = i.split('/')[2]
                #     message = add_file(i, filename, message)
    
                # b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
                # b64_string = b64_bytes.decode()
                media = MediaIoBaseUpload(BytesIO(message.as_bytes()), mimetype='message/rfc822', resumable=True)
                
            email_body = {'message': {'threadId': email_data['threadId']}}
            draft = service.users().drafts().create(userId='me', body=email_body, media_body=media).execute()
            message = service.users().drafts().send(userId='me', body={ 'id': draft['id'] }).execute()
            return message['id'], True, from_mail_id
        else:
            message = multipart.MIMEMultipart()
            from_mail_id = "product@consultadd.com"
            subject = mail_data["subject"]
            message = set_mail_config(mail_data["to"], from_mail_id, mail_data["cc"], mail_data["bcc"], subject, message) 
            
            if reply_to is None:
                body = render_to_string(mail_data["template"], mail_data["context"])
                body = body.replace("\\n", "<br>").replace(";newline;", "<br>").replace(
                    "\\t", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
                message.attach(MIMEText(body,'html'))
                
                file_size = False
                if len(mail_data["attachments"]) > 0:
                    file_size = add_attachments(message,mail_data["attachments"])
                    
                if file_size:
                    return str("Email size is more then 25 MB"), False, None
                                    
                # for i in mail_data["attachments"]:
                #     filename = i.split('/')[2]
                #     message = add_file(i, filename, message)
                media = MediaIoBaseUpload(BytesIO(message.as_bytes()), mimetype='message/rfc822', resumable=True)
                # b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
                # b64_string = b64_bytes.decode()
                message = (service.users().messages().send(userId="me", media_body=media).execute())
                return message['id'], True, from_mail_id
    except Exception as error:
        write_exception(message=error, request=request)
        invalid_keys = ['template', 'context']
        data = {x: mail_data[x] for x in mail_data if x not in invalid_keys}
        write_info(message=str(data), function='send_email_attachment_multiple', request=request)
        return str(error), False, None
