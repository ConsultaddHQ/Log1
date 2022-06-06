from django.core.management import BaseCommand

from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_test_update')
        try:
            count = 0
            consultants = Consultant.objects.exclude(current_city=None)
            for consultant in consultants:
                if consultant.timezone:
                    continue
                elif consultant.current_city:
                    try:
                        count = count + 1
                        timezone = get_timezone(consultant.current_city)
                        consultant.timezone = timezone
                        consultant.save()
                    except Exception:
                        print(f"{consultant.name} ---> not found")
                        continue
                else:
                    print(consultant.id, consultant.current_city)
                    continue
            print(count)
        except Exception as error:
            print(consultant.current_city)
            print(error)
            create_cron_error(job, error)
