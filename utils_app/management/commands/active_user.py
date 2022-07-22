import csv
import random

from django.db.models import Q

from employee.models import User
from log1.utils import write_exception
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            users = User.objects.filter(role__name='engineer', is_active=True)
            for user in users:
                user.technology = [random.choice(['Java', 'Python', 'ReactJS']), random.choice(['AWS', 'SQL'])]
                user.shift = random.choice(['morning', 'general', 'evening', 'afternoon'])
                user.save()
        except Exception as error:
            write_exception(message=error)
