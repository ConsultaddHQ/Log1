import os
import json
import random
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType

from employee.models import User
from attachment.models import Attachment
from attachment import views


def get_time_filter(queryset, filter_by):
    if filter_by == 'today':
        queryset = queryset.filter(created__date=date.today())

    elif filter_by == 'last_day':
        today = date.today()
        day = date.today().weekday()
        if day == 0:
            last_day = today - timedelta(days=3)
        else:
            last_day = today - timedelta(days=1)
        queryset = queryset.filter(created__date=last_day)

    elif filter_by == 'week':
        today = date.today()
        start_of_week = today - timedelta(today.weekday())
        start_of_week = start_of_week - timedelta(days=7)
        end_of_week = start_of_week + timedelta(days=6)
        queryset = queryset.filter(created__gte=start_of_week, created__lte=end_of_week)

    elif filter_by == 'last_month':
        last = date.today().replace(day=1) - timedelta(days=1)
        first = last.replace(day=1)
        queryset = queryset.filter(created__range=[first, last])

    elif filter_by == 'this_month':
        first = date.today().replace(day=1)
        last = date.today()
        queryset = queryset.filter(created__range=[first, last])

    return queryset


def get_time_filter_by_start(queryset, filter_by):
    if filter_by == 'today':
        queryset = queryset.filter(start_time__date=date.today())

    elif filter_by == 'last_day':
        today = date.today()
        day = date.today().weekday()
        if day == 0:
            last_day = today - timedelta(days=3)
        else:
            last_day = today - timedelta(days=1)
        queryset = queryset.filter(start_time__date=last_day)

    elif filter_by == 'week':
        last = date.today() - timedelta(days=1)
        first = last - timedelta(days=7)
        queryset = queryset.filter(created__range=[first, last])

    elif filter_by == 'last_month':
        last = date.today().replace(day=1) - timedelta(days=1)
        first = last.replace(day=1)
        queryset = queryset.filter(start_time__range=[first, last])

    elif filter_by == 'this_month':
        first = date.today().replace(day=1)
        last = date.today()
        queryset = queryset.filter(start_time__range=[first, last])

    return queryset


def post_msg_using_webhook(url, data):
    try:
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp
    except Exception as error:
        print(error)
        return None


def password_generator(password_length=10, strength=3):
    lower = "abcdefghijklmnopqrstuvwxyz"
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()"
    password = ""

    # if strength selected is strong
    if strength == 1:
        for i in range(0, password_length):
            password = password + random.choice(lower)
        return password

    # if strength selected is medium
    elif strength == 2:
        for i in range(0, password_length):
            password = password + random.choice(upper)
        return password

    # if strength selected is strong
    else:
        for i in range(0, password_length):
            password = password + random.choice(digits)
        return password


def html_to_text(html):
    html = html.replace('<strong>', '**').replace('</strong>', '**').replace('<em>', '_').replace('</em>', '_')
    soup = BeautifulSoup(html, features="html.parser")
    return soup.get_text('\n')


def beats_to_log1(file_name, obj_id, doc_type, model):
    try:
        content_type = ContentType.objects.get(model=model)
        creator = User.objects.get(employee_id=1000)
        path = views.download_s3_object_beats(file_name)
        local_file = open(path, 'rb')
        file = ContentFile(local_file.read())
        attachment = Attachment.objects.create(
            creator=creator,
            object_id=obj_id,
            attachment_type=doc_type,
            content_type_id=content_type.id,
        )
        attachment.attachment_file.save(path, file, save=True)
        attachment.save()
        os.remove(path)
        return True, path
    except Exception as error:
        return False, error
