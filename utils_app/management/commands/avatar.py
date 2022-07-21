import os
import magic

from django.core.management import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile

from employee.models import User


class Command(BaseCommand):
    help = "This is one time command to move user avatar to AWS-S3 bucket"

    def handle(self, *args, **options):
        try:
            for file in os.listdir('media/avatar'):
                file_name = file.split('.')
                if file_name and file_name[1] == 'png':
                    try:
                        emp_id = None
                        emp_id = int(file_name[0])
                        us = User.objects.get(employee_id=emp_id)
                        f = open(f'media/avatar/{file}', 'rb+')
                        mime = magic.Magic(mime=True)
                        file_content_type = mime.from_file(f.name)
                        file = InMemoryUploadedFile(f, None, f.name, file_content_type, f.tell(), None)
                        us.avatar = file
                        us.save()
                    except Exception as error:
                        print(f"{error} -- {emp_id}")
                        continue
        except Exception as error:
            print(error)
