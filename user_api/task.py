import logging
import requests
from celery import shared_task
from django.db.models import Q
from importlib import import_module
from django.contrib.contenttypes.models import ContentType

from log1.utils import write_exception, write_info, log_celery_success, log_celery_error
from user_api.models import WebhookEndpoint, TriggerEvent


def import_from_path(path):
    """Dynamically import a class from a string path"""
    module_path, class_name = path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, class_name)


@shared_task(bind=True, queue='trigger_processing', max_retries=3)
def process_trigger(self, payload, request):
    try:
        content_type = ContentType.objects.get(id=payload.get("content_type_id"))
        trigger_event_query = Q(content_type=content_type)

        if payload.get("event_names"):
            trigger_event_query |= Q(name__in=payload.get("event_names"))

        # Get all events with prefetch_related to reduce queries
        events = TriggerEvent.objects.filter(trigger_event_query).distinct('id').order_by('id').prefetch_related(
            'webhook_endpoint'
        )

        serializer_map = dict()
        for event in events:
            if event.serializer_path not in serializer_map:
                serializer_map[event.serializer_path] = []
            serializer_map[event.serializer_path].append(event)

        # Process each unique serializer group
        for serializer_path, events_group in serializer_map.items():
            try:
                # Get first event in group (all share same serializer)
                event_obj = events_group[0]
                model = event_obj.content_type.model_class()
                model_instance = model.objects.get(id=payload.get("object_id"))

                # Prepare filter and get instance
                filter_key = event_obj.model_filter_relation.replace(".", "__")
                if event_obj.object_id_path:
                    instance = getattr(model_instance, event_obj.object_id_path)
                else:
                    instance = model_instance
                if not instance:
                    continue

                # Single serializer call for all events in this group
                serializer_class = import_from_path(serializer_path)
                event_data = serializer_class(instance).data

                # Collect all webhooks for these events
                webhook_ids = set()
                for event in events_group:
                    webhook_ids.update(
                        event.webhook_endpoint
                        .filter(is_active=True)
                        .values_list('id', flat=True)
                    )

                # Bulk deliver webhooks
                for webhook_id in webhook_ids:
                    deliver_webhook.delay(
                        request=request,
                        webhook_id=webhook_id,
                        event_data=event_data,
                        event_type=event_obj.name
                    )

            except Exception as error:
                log_celery_error(
                    message=f"Error processing serializer group {serializer_path}: {str(error)}",
                    function_name="process_trigger",
                    task_id=self.request.id,
                )
                continue

    except Exception as e:
        log_celery_error(
            message=f"Trigger processing failed: {str(e)}",
            function_name="process_trigger",
            task_id=self.request.id,
        )
        self.retry(exc=e, countdown=60)


@shared_task(bind=True, queue='webhook_delivery', max_retries=3)
def deliver_webhook(self, webhook_id, event_data, event_type, request):
    """
    Second queue: Actually deliver the webhook
    """
    unique_object_id = None
    try:
        webhook_obj = WebhookEndpoint.objects.get(id=webhook_id)
        if type(event_data) is not list:
            unique_object_id = event_data.get("id")
            event_data = [event_data]
        else:
            unique_object_id = event_data[0].get("id")
        response = requests.post(
            webhook_obj.target_url, headers=webhook_obj.headers, timeout=10, json=event_data
        )
        response.raise_for_status()

        log_celery_success(
            message=f"Webhook delivered to {webhook_obj.target_url} for {event_type}",
            function_name="deliver_webhook",
            task_id=self.request.id,
            extra_info={"unique_object_id": unique_object_id, "event_type": event_type}
        )
    except requests.exceptions.RequestException as e:
        log_celery_error(
            message=f"Webhook delivery failed (attempt {self.request.retries + 1}): {str(e)}",
            function_name="deliver_webhook",
            task_id=self.request.id,
            extra_info={"webhook_id": webhook_id, "unique_object_id": unique_object_id, "event_type": event_type}
        )
        self.retry(exc=e, countdown=2 ** self.request.retries)
    except Exception as e:
        log_celery_error(
            message=f"Unexpected error: {str(e)}",
            function_name="deliver_webhook",
            task_id=self.request.id,
            extra_info={"webhook_id": webhook_id, "unique_object_id": unique_object_id, "event_type": event_type}
        )
