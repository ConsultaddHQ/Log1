from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .serializers import *
from notifications.signals import notify

User = get_user_model()


def get_all_notifications(data):
    """
        return all notification in a notify session.
    """
    uri = data['uri']
    user_id = data['user_id']
    user = get_object_or_404(User, id=user_id)
    if user_id:
        queryset = Notification.objects.filter(url=uri, recipient=user).order_by('-created')
    else:
        queryset = Notification.objects.filter(url=uri).order_by('-created')

    result = {"results": queryset}

    return result


def send_notification(self, data):
    """
        create a new message in a chats session.
    """

    uri = data['employee_id']
    user = data['user']
    if not User.objects.filter(employee_id=uri).first():
        return False

    notification = Notification.objects.create(
        source=user,
        source_display_name=user.full_name,
        category=data['level'],
        action=data['verb'],
        is_read=False,
        recipient=User.objects.get(employee_id=uri),
        short_description=data['message'],
        create_date=str(timezone.now()),
        url=uri,
        extra_data={'uri': uri}
    )

    notif_args = {
        'extra_data': {
            'uri': uri,
            'message': NotificationSerializer(notification).data
        }
    }
    notify.send(
        sender=self.__class__, **notif_args, channels=['websocket']
    )
    return True
