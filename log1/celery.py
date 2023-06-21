"""Celery init."""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'log1.settings')

APP = Celery('log1')
APP.config_from_object('django.conf:settings', namespace='CELERY')

APP.autodiscover_tasks()

if __name__ == '__main__':
    APP.start()
