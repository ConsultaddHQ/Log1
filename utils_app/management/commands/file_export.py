import io
import json
import pickle
import os.path

from django.core.management import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from employee.models import User
from consultant.models import Consultant
from attachment.models import Attachment


def download_files(service, file_id, name):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    path = name
    with io.open(path, 'wb') as f:
        fh.seek(0)
        f.write(fh.read())
    return path


def upload_files(docs, service, doc_type, consultant, creator, content_type):
    for doc in docs:
        path = download_files(service, doc['id'], doc['name'])
        local_file = open(path, 'rb')
        djangofile = ContentFile(local_file.read())
        attachment = Attachment.objects.create(
            creator=creator,
            object_id=consultant.id,
            attachment_type=doc_type,
            content_type=content_type,
        )
        attachment.attachment_file.save(path, djangofile, save=True)
        attachment.save()
        os.remove(path)


class Command(BaseCommand):
    # A command must define handle()
    def handle(self, *args, **options):

        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        else:
            print("File not found")

        service = build('drive', 'v3', credentials=creds)
        file = open("items2.json", 'r')
        data = json.loads(file.read())
        file.close()

        creator = User.objects.get(employee_id=1000)
        content_type = ContentType.objects.get(model='consultant')
        for email, docs in data.items():
            consultant = Consultant.objects.filter(email=email)
            if consultant:
                consultant = consultant.first()
                upload_files(docs, service, 'misc', consultant, creator, content_type)
