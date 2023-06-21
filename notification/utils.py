import os
from pyfcm import FCMNotification
from django.contrib.contenttypes.models import ContentType

from notification.models import Notification, FCMDevice

push_service = FCMNotification(api_key=os.environ.get('FCM_SERVER_KEY'))

parent_model_classes = [
    ('submission', ['interview', 'test', 'project', 'projectsupport']),
    ('consultant', ['consultantraterevision', 'consultantmarketing', 'consultantexit', 'feedback', 'workauth'
                    'education', 'experience', 'payrollemployer', 'consultantprofile', 'consultantexit'])
]


def get_parent_model(model_name):
    for tab in parent_model_classes:
        if model_name in tab[1]:
            return tab[0]
    return None


def create_notification(user_list, data):
    try:
        recipient_content_type = ContentType.objects.get(model=data['recipient_user_type'])
        sender_content_type = ContentType.objects.get(model=data['sender_user_type'])
        target_content_type = ContentType.objects.get(model=data['target_type'])
        if "parent_type" in data:
            try:
                parent_content_type = ContentType.objects.get(model=data['parent_type'])
            except ContentType.DoesNotExist:
                parent_content_type = None
        else:
            parent_content_type = None

        if "parent_id" in data:
            parent_object_id = data["parent_id"]
        else:
            parent_object_id = None

        for user in user_list:
            Notification.objects.create(
                title=data["title"],
                recipient_object_id=user.id,
                description=data["description"],
                category=data["category"].lower(),
                parent_object_id=parent_object_id,
                sender_object_id=data["sender_id"],
                target_object_id=data["target_id"],
                sender_content_type=sender_content_type,
                parent_content_type=parent_content_type,
                target_content_type=target_content_type,
                recipient_content_type=recipient_content_type,
            )
        return False
    except Exception as error:
        return error


def push_notification(object_ids, message_body):
    try:
        if os.environ.get('ENV', 'local') == 'prod':
            for obj_id in object_ids:
                registration_ids = list(
                    FCMDevice.objects.filter(object_id=obj_id, content_type__model='user'
                                             ).values_list('device_id', flat=True))
                message_body['data']['count'] = Notification.objects.filter(recipient_object_id=obj_id, unread=True,
                                                                            deleted=False).count()
                push_service.notify_multiple_devices(
                    registration_ids=registration_ids,
                    message_title=message_body['title'],
                    message_body=message_body['body'],
                    data_message=message_body,
                )
        return False
    except Exception as error:
        return error


def push_notification_consultant(registration_ids, message_body):
    try:
        if os.environ.get('ENV', 'local') == 'prod':
            push_service.notify_multiple_devices(
                registration_ids=registration_ids,
                message_title=message_body['title'],
                message_body=message_body['body'],
                data_message=message_body,
            )
        return False
    except Exception as error:
        return error
