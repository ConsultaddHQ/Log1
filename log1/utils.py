import os
import ssl
import sys

import certifi
import yaml
import json
import random
import logging
import requests
from constance import config
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from datetime import date, timedelta
from logging.config import dictConfig
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

DONT_HAVE_ACCESS = "You don't have access"
ERROR_MSG = "Something went wrong. Please contact support"


def load_config(file_path):
    try:
        with open(file_path, 'r') as f:
            dictConfig(yaml.safe_load(f))
    except FileExistsError as error:
        logger.error(error)


def log_request(request):
    """Log the request"""
    address = request.META['REMOTE_ADDR']
    method = str(getattr(request, 'method', '')).upper()
    request_path = str(getattr(request, 'path', ''))
    try:
        text = f"Error : [{method}] : {address} : {request_path} : "
        if type(request.user) is not AnonymousUser:
            if hasattr(request.user, "name"):
                text += f"Consultant : {request.user.id} : {request.user.name} : "
            else:
                text += f"Employee : {request.user.id} : {request.user.employee_name} : "
        else:
            text += f"User : 0 : AnonymousUser : "
        return text
    except Exception as error:
        text = f"Exception : [{method}] : {address} : {request_path} : {error} : "
        return text


def write_info(message, function, request=None):
    text = ''
    if request:
        text += log_request(request)
    text += f"Function - {function} : Message - {message}"
    logger.info(text)


def write_exception(message, request=None):
    text = ""
    if request:
        text += log_request(request)
    try:
        _, _, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        function = f.f_code.co_name
        filename = f.f_code.co_filename
        classname = None
        if 'self' in f.f_locals:
            classname = f.f_locals["self"].__class__.__name__
        data = f'Error in {filename} : Class - {classname} : Function - {function} : Line no - ' \
               f'{lineno} : Message - {message}'
        logger.error(text + data)
    except Exception as error:
        text += f"Exception in {error}"
        logger.error(text)


def get_page_limits(request):
    try:
        if request.GET.get("page") == 'undefined':
            return 1, 10
        page = int(request.GET.get("page", 1))
        if 'page_size' in request.GET:
            page_size = int(request.GET.get("page_size", 10))
        elif 'size' in request.GET:
            page_size = int(request.GET.get("size", 10))
        else:
            page_size = 10
        return page * page_size - page_size, page * page_size
    except Exception as error:
        write_exception(message=error, request=request)
        return 1, 10


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
        data = json.dumps(data)
        data = data.replace("\\n", "\n")
        data = data.replace("\\t", "\t")
        headers = {'Content-Type': 'application/json'}
        if os.environ.get("ENV", "local") == 'prod':
            resp = requests.post(url, headers=headers, data=data)
            return resp, "ok"
        else:
            url = "https://hooks.slack.com/services/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"
            resp = requests.post(url, headers=headers, data=data)
            return resp, "ok"
    except Exception as error:
        write_exception(error)
        return error, "error"


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
    if html:
        html = html.replace('<strong>', '**').replace('</strong>', '**').replace('<em>', '_').replace('</em>', '_')
        soup = BeautifulSoup(html, features="html.parser")
        return soup.get_text('\n')
    return html


def send_personalized_message(user_id: str, message: str) -> tuple:
    try:

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        client = WebClient(token=config.SLACK_TOKEN, ssl=ssl_context)

        if os.environ.get("ENV", "local") == 'prod':
            resp = client.chat_postMessage(channel=user_id, blocks=message)
        else:
            user_id = 'U03L0TGDPAQ'
            resp = client.chat_postMessage(channel=user_id, blocks=message)
        return resp, "ok"
    except Exception as error:
        write_exception(error)
        return error, "error"
