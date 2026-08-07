"""Celery init."""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'log1.settings')

APP = Celery('log1')

APP.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'exchange_type': 'direct',
        'routing_key': 'default'
    },
    'trigger_processing': {
        'exchange': 'trigger_processing',
        'exchange_type': 'direct',
        'routing_key': 'trigger_processing'
    },
    'webhook_delivery': {
        'exchange': 'webhook_delivery',
        'exchange_type': 'direct',
        'routing_key': 'webhook_delivery'
    }
}

# Route specific tasks to dedicated queues
APP.conf.task_routes = {
    'user_api.tasks.process_trigger': {'queue': 'trigger_processing'},
    'user_api.tasks.deliver_webhook': {'queue': 'webhook_delivery'},
    # All other tasks will go to default queue automatically
}

APP.config_from_object('django.conf:settings', namespace='CELERY')

APP.autodiscover_tasks()

if __name__ == '__main__':
    APP.start()
