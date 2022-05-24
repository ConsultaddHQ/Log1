from django.core.management import BaseCommand
from employee.models import User
from log1.utils import write_exception
from datetime import datetime
from django.db.models import Q
from django.utils import timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            filter_user = User.objects.filter(Q(employee_id__gt=10000) |
                                              Q(date_joined__gt=datetime(2022, 5, 1,
                                                                         tzinfo=timezone.utc)))
            user_number = len(filter_user)
            filter_user.delete()
            print(f"{user_number} users deleted successfully")
        except Exception as error:
            write_exception(message=error)
