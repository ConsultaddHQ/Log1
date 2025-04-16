import logging
import requests
from celery import shared_task
from django.db.models import Q
from importlib import import_module
from django.contrib.contenttypes.models import ContentType

from log1.utils import write_exception, write_info
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
                write_exception(f"Error processing serializer group {serializer_path}: {str(error)}", request)
                continue

    except Exception as e:
        write_exception(f"Trigger processing failed: {str(e)}", request)
        self.retry(exc=e, countdown=60)


@shared_task(bind=True, queue='webhook_delivery', max_retries=3)
def deliver_webhook(self, webhook_id, event_data, event_type, request):
    """
    Second queue: Actually deliver the webhook
    """
    try:
        webhook_obj = WebhookEndpoint.objects.get(id=webhook_id)
        if type(event_data) is not list:
            event_data = [event_data]
        response = requests.post(
            webhook_obj.target_url, headers=webhook_obj.headers, timeout=10, json=event_data
        )
        response.raise_for_status()

        write_info(f"Webhook delivered to {webhook_obj.target_url} for {event_type}", function=deliver_webhook)

    except requests.exceptions.RequestException as e:
        write_info(f"Webhook delivery failed (attempt {self.request.retries + 1}): {str(e)}", function=deliver_webhook)
        self.retry(exc=e, countdown=2 ** self.request.retries)
    except Exception as e:
        write_exception(f"Unexpected webhook delivery error: {str(e)}", request)
