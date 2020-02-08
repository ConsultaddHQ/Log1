import logging
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

CATEGORY_CHOICES = (
    ('info', 'Info'),
    ('alert', 'Alert'),
    ('pending', 'Pending'),
    ('rejected', 'Rejected'),
)

DEVICE_TYPES = (
    (u'ios', u'ios'),
    (u'web', u'web'),
    (u'android', u'android'),
)

logger = logging.getLogger(__name__)


class NotificationQuerySet(models.query.QuerySet):
    """ Notification QuerySet """
    def unread(self, user, user_type):
        """Return only unread items in the current queryset"""
        return self.filter(
            unread=True, deleted=False,
            recipient_object_id=user.id,
            recipient_content_type__model=user_type,
        ).order_by('timestamp')

    def mark_all_as_read(self, recipient, user_type):
        """Mark as read any unread messages in the current queryset.
        Optionally, filter these by recipient first.
        """
        qset = self.unread(recipient, user_type)
        return qset.update(unread=False)

    def active(self, recipient, user_type):
        """Return only active(un-deleted) items in the current queryset"""
        queryset = self.filter(
            deleted=False,
            recipient_object_id=recipient.id,
            recipient_content_type__model=user_type,
        )
        return queryset

    def mark_all_as_deleted(self, recipient, user_type):
        """Mark current queryset as deleted.
        Optionally, filter by recipient first.
        """
        qset = self.active(recipient, user_type)
        return qset.update(deleted=True)


class FCMDevice(models.Model):
    active = models.BooleanField(_("Is active"), default=True)
    type = models.CharField(choices=DEVICE_TYPES, max_length=10, blank=True, null=True)
    name = models.CharField(_("Name of Device"), max_length=255, blank=True, null=True)
    date_created = models.DateTimeField(_("Creation date"), auto_now_add=True, null=True)
    device_id = models.CharField(_("Device ID"), primary_key=True, db_index=True, max_length=300)

    object_id = models.CharField(_('Object Id'), max_length=40)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")


class Notification(models.Model):
    description = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False, db_index=True)
    emailed = models.BooleanField(default=False, db_index=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    unread = models.BooleanField(default=True, blank=False, db_index=True)
    category = models.CharField(choices=CATEGORY_CHOICES, default='alert', max_length=20)

    recipient_object_id = models.PositiveIntegerField()
    recipient_content_type = models.ForeignKey(
        ContentType,
        null=True,
        on_delete=models.SET_NULL,
        related_name='recipient_notification'
    )
    recipient_content_object = GenericForeignKey('recipient_content_type', 'recipient_object_id')

    sender_object_id = models.PositiveIntegerField()
    sender_content_type = models.ForeignKey(
        ContentType,
        null=True,
        on_delete=models.SET_NULL,
        related_name='sender_notification'
    )
    sender_content_object = GenericForeignKey('sender_content_type', 'sender_object_id')

    target_object_id = models.PositiveIntegerField()
    target_content_type = models.ForeignKey(
        ContentType,
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='target_notification'
    )
    target_content_object = GenericForeignKey('target_content_type', 'target_object_id')

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        ctx = {
            'title': self.title,
            'timesince': self.timesince()
        }
        return u'%(title)s %(timesince)s ago' % ctx

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save()

    def mark_as_deleted(self):
        if not self.deleted:
            self.deleted = True
            self.save()

    def mark_not_deleted(self):
        if self.deleted:
            self.deleted = False
            self.save()
