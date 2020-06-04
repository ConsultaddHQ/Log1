import json
import random
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta


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
        queryset = queryset.filter(created__gte=start_of_week)

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
        today = date.today()
        start_of_week = today - timedelta(today.weekday())
        queryset = queryset.filter(start_time__gte=start_of_week)

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
