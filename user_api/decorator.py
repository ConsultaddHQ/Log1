from functools import wraps
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from log1.utils import write_exception
from user_api.task import process_trigger


def webhook_notify(events=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            print("executed")
            response = view_func(self, request, *args, **kwargs)

            if hasattr(response, 'status_code') and response.status_code in [200, 201, 202, 204]:
                try:
                    model = self.queryset.model
                    content_type = ContentType.objects.get_for_model(model)

                    if isinstance(events, str):
                        event_names = [e.strip() for e in events.split(',') if e.strip()]
                    elif isinstance(events, (list, tuple)):
                        event_names = list(events)
                    else:
                        event_names = None

                    response_data = {
                        'event_names': event_names,
                        'content_type_id': content_type.id,
                        'timestamp': timezone.now().isoformat(),
                        'object_id': response.data.get('trigger_payload').get("object_id")
                    }
                    process_trigger.delay(
                        payload=response_data, request=request
                    )

                except Exception as error:
                    write_exception(str(error), request)

            return response

        return wrapper

    return decorator
